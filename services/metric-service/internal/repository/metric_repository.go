package repository

import (
	"context"
	"fmt"
	"time"

	"github.com/google/uuid"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"go.uber.org/zap"

	"github.com/wanllmdb/metric-service/internal/model"
)

type MetricRepository struct {
	db     *pgxpool.Pool
	logger *zap.Logger
}

func NewMetricRepository(db *pgxpool.Pool, logger *zap.Logger) *MetricRepository {
	return &MetricRepository{
		db:     db,
		logger: logger,
	}
}

// BatchWrite inserts multiple metrics in a single transaction
func (r *MetricRepository) BatchWrite(ctx context.Context, metrics []model.Metric) error {
	if len(metrics) == 0 {
		return nil
	}

	tx, err := r.db.Begin(ctx)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback(ctx)

	batch := &pgx.Batch{}
	for _, metric := range metrics {
		batch.Queue(
			`INSERT INTO metrics (time, run_id, metric_name, step, value, metadata)
			 VALUES ($1, $2, $3, $4, $5, $6)`,
			metric.Time, metric.RunID, metric.MetricName, metric.Step, metric.Value, metric.Metadata,
		)
	}

	br := tx.SendBatch(ctx, batch)
	defer br.Close()

	// Execute all batched queries
	for i := 0; i < len(metrics); i++ {
		if _, err := br.Exec(); err != nil {
			return fmt.Errorf("failed to insert metric %d: %w", i, err)
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	r.logger.Info("Batch write completed", zap.Int("count", len(metrics)))
	return nil
}

// BatchWriteSystemMetrics inserts multiple system metrics
func (r *MetricRepository) BatchWriteSystemMetrics(ctx context.Context, metrics []model.SystemMetric) error {
	if len(metrics) == 0 {
		return nil
	}

	tx, err := r.db.Begin(ctx)
	if err != nil {
		return fmt.Errorf("failed to begin transaction: %w", err)
	}
	defer tx.Rollback(ctx)

	batch := &pgx.Batch{}
	for _, metric := range metrics {
		batch.Queue(
			`INSERT INTO system_metrics (time, run_id, metric_type, value, metadata)
			 VALUES ($1, $2, $3, $4, $5)`,
			metric.Time, metric.RunID, metric.MetricType, metric.Value, metric.Metadata,
		)
	}

	br := tx.SendBatch(ctx, batch)
	defer br.Close()

	for i := 0; i < len(metrics); i++ {
		if _, err := br.Exec(); err != nil {
			return fmt.Errorf("failed to insert system metric %d: %w", i, err)
		}
	}

	if err := tx.Commit(ctx); err != nil {
		return fmt.Errorf("failed to commit transaction: %w", err)
	}

	r.logger.Info("System metrics batch write completed", zap.Int("count", len(metrics)))
	return nil
}

// GetRunMetrics retrieves all metrics for a specific run
func (r *MetricRepository) GetRunMetrics(ctx context.Context, runID uuid.UUID, params model.MetricQueryParams) ([]model.Metric, error) {
	query := `SELECT time, run_id, metric_name, step, value, metadata
	          FROM metrics
	          WHERE run_id = $1`
	args := []interface{}{runID}
	argIdx := 2

	if params.StartTime != nil {
		query += fmt.Sprintf(" AND time >= $%d", argIdx)
		args = append(args, *params.StartTime)
		argIdx++
	}

	if params.EndTime != nil {
		query += fmt.Sprintf(" AND time <= $%d", argIdx)
		args = append(args, *params.EndTime)
		argIdx++
	}

	if params.MinStep != nil {
		query += fmt.Sprintf(" AND step >= $%d", argIdx)
		args = append(args, *params.MinStep)
		argIdx++
	}

	if params.MaxStep != nil {
		query += fmt.Sprintf(" AND step <= $%d", argIdx)
		args = append(args, *params.MaxStep)
		argIdx++
	}

	if params.MetricName != "" {
		query += fmt.Sprintf(" AND metric_name = $%d", argIdx)
		args = append(args, params.MetricName)
		argIdx++
	}

	query += " ORDER BY time DESC"

	if params.Limit > 0 {
		query += fmt.Sprintf(" LIMIT $%d", argIdx)
		args = append(args, params.Limit)
	}

	rows, err := r.db.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query metrics: %w", err)
	}
	defer rows.Close()

	var metrics []model.Metric
	for rows.Next() {
		var m model.Metric
		if err := rows.Scan(&m.Time, &m.RunID, &m.MetricName, &m.Step, &m.Value, &m.Metadata); err != nil {
			return nil, fmt.Errorf("failed to scan metric: %w", err)
		}
		metrics = append(metrics, m)
	}

	return metrics, nil
}

// GetMetricHistory retrieves history for a specific metric
func (r *MetricRepository) GetMetricHistory(ctx context.Context, runID uuid.UUID, metricName string, params model.MetricQueryParams) ([]model.Metric, error) {
	params.MetricName = metricName
	return r.GetRunMetrics(ctx, runID, params)
}

// GetLatestMetric retrieves the most recent value for a specific metric
func (r *MetricRepository) GetLatestMetric(ctx context.Context, runID uuid.UUID, metricName string) (*model.Metric, error) {
	query := `SELECT time, run_id, metric_name, step, value, metadata
	          FROM metrics
	          WHERE run_id = $1 AND metric_name = $2
	          ORDER BY time DESC
	          LIMIT 1`

	var m model.Metric
	err := r.db.QueryRow(ctx, query, runID, metricName).Scan(
		&m.Time, &m.RunID, &m.MetricName, &m.Step, &m.Value, &m.Metadata,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to query latest metric: %w", err)
	}

	return &m, nil
}

// GetMetricStats retrieves statistics for a specific metric
func (r *MetricRepository) GetMetricStats(ctx context.Context, runID uuid.UUID, metricName string) (*model.MetricStats, error) {
	query := `SELECT
	            metric_name,
	            COUNT(*) as count,
	            MIN(value) as min_value,
	            MAX(value) as max_value,
	            AVG(value) as avg_value,
	            STDDEV(value) as std_dev,
	            MIN(time) as first_time,
	            MAX(time) as last_time
	          FROM metrics
	          WHERE run_id = $1 AND metric_name = $2
	          GROUP BY metric_name`

	var stats model.MetricStats
	err := r.db.QueryRow(ctx, query, runID, metricName).Scan(
		&stats.MetricName,
		&stats.Count,
		&stats.MinValue,
		&stats.MaxValue,
		&stats.AvgValue,
		&stats.StdDev,
		&stats.FirstTime,
		&stats.LastTime,
	)
	if err == pgx.ErrNoRows {
		return nil, nil
	}
	if err != nil {
		return nil, fmt.Errorf("failed to query metric stats: %w", err)
	}

	return &stats, nil
}

// GetSystemMetrics retrieves system metrics for a specific run
func (r *MetricRepository) GetSystemMetrics(ctx context.Context, runID uuid.UUID, startTime, endTime *time.Time, limit int) ([]model.SystemMetric, error) {
	query := `SELECT time, run_id, metric_type, value, metadata
	          FROM system_metrics
	          WHERE run_id = $1`
	args := []interface{}{runID}
	argIdx := 2

	if startTime != nil {
		query += fmt.Sprintf(" AND time >= $%d", argIdx)
		args = append(args, *startTime)
		argIdx++
	}

	if endTime != nil {
		query += fmt.Sprintf(" AND time <= $%d", argIdx)
		args = append(args, *endTime)
		argIdx++
	}

	query += " ORDER BY time DESC"

	if limit > 0 {
		query += fmt.Sprintf(" LIMIT $%d", argIdx)
		args = append(args, limit)
	}

	rows, err := r.db.Query(ctx, query, args...)
	if err != nil {
		return nil, fmt.Errorf("failed to query system metrics: %w", err)
	}
	defer rows.Close()

	var metrics []model.SystemMetric
	for rows.Next() {
		var m model.SystemMetric
		if err := rows.Scan(&m.Time, &m.RunID, &m.MetricType, &m.Value, &m.Metadata); err != nil {
			return nil, fmt.Errorf("failed to scan system metric: %w", err)
		}
		metrics = append(metrics, m)
	}

	return metrics, nil
}
