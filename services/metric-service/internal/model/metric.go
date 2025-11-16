package model

import (
	"time"

	"github.com/google/uuid"
)

type Metric struct {
	Time       time.Time              `json:"time"`
	RunID      uuid.UUID              `json:"run_id"`
	MetricName string                 `json:"metric_name"`
	Step       *int                   `json:"step"`
	Value      float64                `json:"value"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

type SystemMetric struct {
	Time       time.Time              `json:"time"`
	RunID      uuid.UUID              `json:"run_id"`
	MetricType string                 `json:"metric_type"` // cpu, gpu, memory, disk, network
	Value      float64                `json:"value"`
	Metadata   map[string]interface{} `json:"metadata,omitempty"`
}

type MetricBatchRequest struct {
	Metrics []Metric `json:"metrics" binding:"required,min=1,max=1000"`
}

type SystemMetricBatchRequest struct {
	Metrics []SystemMetric `json:"metrics" binding:"required,min=1,max=1000"`
}

type MetricQueryParams struct {
	StartTime  *time.Time `form:"start_time"`
	EndTime    *time.Time `form:"end_time"`
	MinStep    *int       `form:"min_step"`
	MaxStep    *int       `form:"max_step"`
	Limit      int        `form:"limit" binding:"min=1,max=10000"`
	MetricName string     `form:"metric_name"`
}

type MetricStats struct {
	MetricName string    `json:"metric_name"`
	Count      int64     `json:"count"`
	MinValue   float64   `json:"min_value"`
	MaxValue   float64   `json:"max_value"`
	AvgValue   float64   `json:"avg_value"`
	StdDev     *float64  `json:"std_dev"`
	FirstTime  time.Time `json:"first_time"`
	LastTime   time.Time `json:"last_time"`
}

type RunMetricsSummary struct {
	RunID   uuid.UUID              `json:"run_id"`
	Metrics map[string]MetricStats `json:"metrics"`
}

type WebSocketMessage struct {
	Type    string      `json:"type"` // "subscribe", "unsubscribe", "metric"
	Payload interface{} `json:"payload"`
}

type SubscribePayload struct {
	RunID       uuid.UUID `json:"run_id"`
	MetricNames []string  `json:"metric_names,omitempty"`
}

type MetricPayload struct {
	Metrics []Metric `json:"metrics"`
}
