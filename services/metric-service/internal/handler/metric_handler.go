package handler

import (
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"go.uber.org/zap"

	"github.com/wanllmdb/metric-service/internal/model"
	"github.com/wanllmdb/metric-service/internal/service"
)

type MetricHandler struct {
	service *service.MetricService
	logger  *zap.Logger
}

func NewMetricHandler(service *service.MetricService, logger *zap.Logger) *MetricHandler {
	return &MetricHandler{
		service: service,
		logger:  logger,
	}
}

// BatchWrite handles batch metric writing
func (h *MetricHandler) BatchWrite(c *gin.Context) {
	var req model.MetricBatchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.service.BatchWrite(c.Request.Context(), req.Metrics); err != nil {
		h.logger.Error("Failed to write metrics", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to write metrics"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"message": "Metrics written successfully",
		"count":   len(req.Metrics),
	})
}

// BatchWriteSystemMetrics handles batch system metric writing
func (h *MetricHandler) BatchWriteSystemMetrics(c *gin.Context) {
	var req model.SystemMetricBatchRequest
	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if err := h.service.BatchWriteSystemMetrics(c.Request.Context(), req.Metrics); err != nil {
		h.logger.Error("Failed to write system metrics", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to write system metrics"})
		return
	}

	c.JSON(http.StatusCreated, gin.H{
		"message": "System metrics written successfully",
		"count":   len(req.Metrics),
	})
}

// GetRunMetrics retrieves all metrics for a run
func (h *MetricHandler) GetRunMetrics(c *gin.Context) {
	runIDStr := c.Param("run_id")
	runID, err := uuid.Parse(runIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid run ID"})
		return
	}

	var params model.MetricQueryParams
	if err := c.ShouldBindQuery(&params); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Set default limit
	if params.Limit == 0 {
		params.Limit = 1000
	}

	metrics, err := h.service.GetRunMetrics(c.Request.Context(), runID, params)
	if err != nil {
		h.logger.Error("Failed to get run metrics", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get metrics"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"run_id":  runID,
		"metrics": metrics,
		"count":   len(metrics),
	})
}

// GetMetricHistory retrieves history for a specific metric
func (h *MetricHandler) GetMetricHistory(c *gin.Context) {
	runIDStr := c.Param("run_id")
	runID, err := uuid.Parse(runIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid run ID"})
		return
	}

	metricName := c.Param("metric_name")
	if metricName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Metric name is required"})
		return
	}

	var params model.MetricQueryParams
	if err := c.ShouldBindQuery(&params); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if params.Limit == 0 {
		params.Limit = 1000
	}

	metrics, err := h.service.GetMetricHistory(c.Request.Context(), runID, metricName, params)
	if err != nil {
		h.logger.Error("Failed to get metric history", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get metric history"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"run_id":      runID,
		"metric_name": metricName,
		"metrics":     metrics,
		"count":       len(metrics),
	})
}

// GetLatestMetric retrieves the latest value for a metric
func (h *MetricHandler) GetLatestMetric(c *gin.Context) {
	runIDStr := c.Param("run_id")
	runID, err := uuid.Parse(runIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid run ID"})
		return
	}

	metricName := c.Param("metric_name")
	if metricName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Metric name is required"})
		return
	}

	metric, err := h.service.GetLatestMetric(c.Request.Context(), runID, metricName)
	if err != nil {
		h.logger.Error("Failed to get latest metric", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get latest metric"})
		return
	}

	if metric == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Metric not found"})
		return
	}

	c.JSON(http.StatusOK, metric)
}

// GetMetricStats retrieves statistics for a metric
func (h *MetricHandler) GetMetricStats(c *gin.Context) {
	runIDStr := c.Param("run_id")
	runID, err := uuid.Parse(runIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid run ID"})
		return
	}

	metricName := c.Param("metric_name")
	if metricName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Metric name is required"})
		return
	}

	stats, err := h.service.GetMetricStats(c.Request.Context(), runID, metricName)
	if err != nil {
		h.logger.Error("Failed to get metric stats", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get metric stats"})
		return
	}

	if stats == nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "Metric not found"})
		return
	}

	c.JSON(http.StatusOK, stats)
}

// GetSystemMetrics retrieves system metrics for a run
func (h *MetricHandler) GetSystemMetrics(c *gin.Context) {
	runIDStr := c.Param("run_id")
	runID, err := uuid.Parse(runIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid run ID"})
		return
	}

	var startTime, endTime *time.Time
	if st := c.Query("start_time"); st != "" {
		t, err := time.Parse(time.RFC3339, st)
		if err == nil {
			startTime = &t
		}
	}
	if et := c.Query("end_time"); et != "" {
		t, err := time.Parse(time.RFC3339, et)
		if err == nil {
			endTime = &t
		}
	}

	limit := 1000
	if l := c.Query("limit"); l != "" {
		if parsedLimit, err := strconv.Atoi(l); err == nil && parsedLimit > 0 {
			limit = parsedLimit
		}
	}

	metrics, err := h.service.GetSystemMetrics(c.Request.Context(), runID, startTime, endTime, limit)
	if err != nil {
		h.logger.Error("Failed to get system metrics", zap.Error(err))
		c.JSON(http.StatusInternalServerError, gin.H{"error": "Failed to get system metrics"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"run_id":  runID,
		"metrics": metrics,
		"count":   len(metrics),
	})
}
