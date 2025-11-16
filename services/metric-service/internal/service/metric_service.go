package service

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/wanllmdb/metric-service/internal/model"
	"github.com/wanllmdb/metric-service/internal/repository"
)

type MetricService struct {
	repo   *repository.MetricRepository
	redis  *redis.Client
	logger *zap.Logger
}

func NewMetricService(repo *repository.MetricRepository, redis *redis.Client, logger *zap.Logger) *MetricService {
	return &MetricService{
		repo:   repo,
		redis:  redis,
		logger: logger,
	}
}

// BatchWrite writes metrics and publishes to Redis for WebSocket streaming
func (s *MetricService) BatchWrite(ctx context.Context, metrics []model.Metric) error {
	// Validate metrics
	if err := s.validateMetrics(metrics); err != nil {
		return err
	}

	// Write to database
	if err := s.repo.BatchWrite(ctx, metrics); err != nil {
		return fmt.Errorf("failed to write metrics: %w", err)
	}

	// Publish to Redis for real-time streaming
	if err := s.publishMetrics(ctx, metrics); err != nil {
		s.logger.Error("Failed to publish metrics to Redis", zap.Error(err))
		// Don't return error, as write succeeded
	}

	// Invalidate cache
	s.invalidateCache(ctx, metrics)

	return nil
}

// BatchWriteSystemMetrics writes system metrics
func (s *MetricService) BatchWriteSystemMetrics(ctx context.Context, metrics []model.SystemMetric) error {
	return s.repo.BatchWriteSystemMetrics(ctx, metrics)
}

// GetRunMetrics retrieves metrics with caching
func (s *MetricService) GetRunMetrics(ctx context.Context, runID uuid.UUID, params model.MetricQueryParams) ([]model.Metric, error) {
	// Try cache first
	cacheKey := s.getRunMetricsCacheKey(runID, params)
	if cached, err := s.getFromCache(ctx, cacheKey); err == nil && cached != nil {
		var metrics []model.Metric
		if err := json.Unmarshal(cached, &metrics); err == nil {
			s.logger.Debug("Cache hit for run metrics", zap.String("run_id", runID.String()))
			return metrics, nil
		}
	}

	// Query from database
	metrics, err := s.repo.GetRunMetrics(ctx, runID, params)
	if err != nil {
		return nil, err
	}

	// Cache the result
	if data, err := json.Marshal(metrics); err == nil {
		s.setCache(ctx, cacheKey, data, 5*time.Minute)
	}

	return metrics, nil
}

// GetMetricHistory retrieves metric history
func (s *MetricService) GetMetricHistory(ctx context.Context, runID uuid.UUID, metricName string, params model.MetricQueryParams) ([]model.Metric, error) {
	return s.repo.GetMetricHistory(ctx, runID, metricName, params)
}

// GetLatestMetric retrieves the latest metric value with caching
func (s *MetricService) GetLatestMetric(ctx context.Context, runID uuid.UUID, metricName string) (*model.Metric, error) {
	cacheKey := fmt.Sprintf("metric:latest:%s:%s", runID.String(), metricName)

	if cached, err := s.getFromCache(ctx, cacheKey); err == nil && cached != nil {
		var metric model.Metric
		if err := json.Unmarshal(cached, &metric); err == nil {
			return &metric, nil
		}
	}

	metric, err := s.repo.GetLatestMetric(ctx, runID, metricName)
	if err != nil {
		return nil, err
	}

	if metric != nil {
		if data, err := json.Marshal(metric); err == nil {
			s.setCache(ctx, cacheKey, data, 1*time.Minute)
		}
	}

	return metric, nil
}

// GetMetricStats retrieves metric statistics
func (s *MetricService) GetMetricStats(ctx context.Context, runID uuid.UUID, metricName string) (*model.MetricStats, error) {
	cacheKey := fmt.Sprintf("metric:stats:%s:%s", runID.String(), metricName)

	if cached, err := s.getFromCache(ctx, cacheKey); err == nil && cached != nil {
		var stats model.MetricStats
		if err := json.Unmarshal(cached, &stats); err == nil {
			return &stats, nil
		}
	}

	stats, err := s.repo.GetMetricStats(ctx, runID, metricName)
	if err != nil {
		return nil, err
	}

	if stats != nil {
		if data, err := json.Marshal(stats); err == nil {
			s.setCache(ctx, cacheKey, data, 5*time.Minute)
		}
	}

	return stats, nil
}

// GetSystemMetrics retrieves system metrics
func (s *MetricService) GetSystemMetrics(ctx context.Context, runID uuid.UUID, startTime, endTime *time.Time, limit int) ([]model.SystemMetric, error) {
	return s.repo.GetSystemMetrics(ctx, runID, startTime, endTime, limit)
}

// Helper methods

func (s *MetricService) validateMetrics(metrics []model.Metric) error {
	for i, m := range metrics {
		if m.RunID == uuid.Nil {
			return fmt.Errorf("metric %d: run_id is required", i)
		}
		if m.MetricName == "" {
			return fmt.Errorf("metric %d: metric_name is required", i)
		}
		if m.Time.IsZero() {
			metrics[i].Time = time.Now()
		}
	}
	return nil
}

func (s *MetricService) publishMetrics(ctx context.Context, metrics []model.Metric) error {
	// Group metrics by run_id for efficient publishing
	metricsByRun := make(map[uuid.UUID][]model.Metric)
	for _, m := range metrics {
		metricsByRun[m.RunID] = append(metricsByRun[m.RunID], m)
	}

	for runID, runMetrics := range metricsByRun {
		payload := model.MetricPayload{Metrics: runMetrics}
		data, err := json.Marshal(payload)
		if err != nil {
			return err
		}

		channel := fmt.Sprintf("metrics:%s", runID.String())
		if err := s.redis.Publish(ctx, channel, data).Err(); err != nil {
			return err
		}
	}

	return nil
}

func (s *MetricService) invalidateCache(ctx context.Context, metrics []model.Metric) {
	for _, m := range metrics {
		// Invalidate latest metric cache
		cacheKey := fmt.Sprintf("metric:latest:%s:%s", m.RunID.String(), m.MetricName)
		s.redis.Del(ctx, cacheKey)

		// Invalidate stats cache
		statsKey := fmt.Sprintf("metric:stats:%s:%s", m.RunID.String(), m.MetricName)
		s.redis.Del(ctx, statsKey)
	}
}

func (s *MetricService) getRunMetricsCacheKey(runID uuid.UUID, params model.MetricQueryParams) string {
	return fmt.Sprintf("metrics:run:%s:%v", runID.String(), params)
}

func (s *MetricService) getFromCache(ctx context.Context, key string) ([]byte, error) {
	return s.redis.Get(ctx, key).Bytes()
}

func (s *MetricService) setCache(ctx context.Context, key string, value []byte, expiration time.Duration) error {
	return s.redis.Set(ctx, key, value, expiration).Err()
}

// SubscribeToMetrics subscribes to Redis channel for real-time metrics
func (s *MetricService) SubscribeToMetrics(ctx context.Context, channel string) *redis.PubSub {
	return s.redis.Subscribe(ctx, channel)
}
