package handler

import (
	"context"
	"encoding/json"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"github.com/redis/go-redis/v9"
	"go.uber.org/zap"

	"github.com/wanllmdb/metric-service/internal/model"
	"github.com/wanllmdb/metric-service/internal/service"
)

var upgrader = websocket.Upgrader{
	ReadBufferSize:  1024,
	WriteBufferSize: 1024,
	CheckOrigin: func(r *http.Request) bool {
		return true // Allow all origins in development
	},
}

type WebSocketHandler struct {
	service *service.MetricService
	logger  *zap.Logger
}

func NewWebSocketHandler(service *service.MetricService, logger *zap.Logger) *WebSocketHandler {
	return &WebSocketHandler{
		service: service,
		logger:  logger,
	}
}

type Client struct {
	conn        *websocket.Conn
	send        chan []byte
	runID       uuid.UUID
	metricNames map[string]bool
	mu          sync.RWMutex
}

// HandleConnection handles WebSocket connections for real-time metrics
func (h *WebSocketHandler) HandleConnection(c *gin.Context) {
	runIDStr := c.Param("run_id")
	runID, err := uuid.Parse(runIDStr)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "Invalid run ID"})
		return
	}

	conn, err := upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		h.logger.Error("Failed to upgrade connection", zap.Error(err))
		return
	}

	client := &Client{
		conn:        conn,
		send:        make(chan []byte, 256),
		runID:       runID,
		metricNames: make(map[string]bool),
	}

	h.logger.Info("WebSocket client connected", zap.String("run_id", runID.String()))

	// Start goroutines
	go h.readPump(client)
	go h.writePump(client)
	go h.subscribePump(client)
}

// readPump reads messages from the WebSocket connection
func (h *WebSocketHandler) readPump(client *Client) {
	defer func() {
		client.conn.Close()
	}()

	client.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	client.conn.SetPongHandler(func(string) error {
		client.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, message, err := client.conn.ReadMessage()
		if err != nil {
			if websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure) {
				h.logger.Error("WebSocket error", zap.Error(err))
			}
			break
		}

		var msg model.WebSocketMessage
		if err := json.Unmarshal(message, &msg); err != nil {
			h.logger.Error("Failed to parse message", zap.Error(err))
			continue
		}

		h.handleMessage(client, &msg)
	}
}

// writePump writes messages to the WebSocket connection
func (h *WebSocketHandler) writePump(client *Client) {
	ticker := time.NewTicker(54 * time.Second)
	defer func() {
		ticker.Stop()
		client.conn.Close()
	}()

	for {
		select {
		case message, ok := <-client.send:
			client.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if !ok {
				client.conn.WriteMessage(websocket.CloseMessage, []byte{})
				return
			}

			if err := client.conn.WriteMessage(websocket.TextMessage, message); err != nil {
				return
			}

		case <-ticker.C:
			client.conn.SetWriteDeadline(time.Now().Add(10 * time.Second))
			if err := client.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// subscribePump subscribes to Redis channel and forwards messages
func (h *WebSocketHandler) subscribePump(client *Client) {
	ctx := context.Background()
	channel := "metrics:" + client.runID.String()

	// Get Redis client from service (we'll need to expose this)
	pubsub := h.service.SubscribeToMetrics(ctx, channel)
	defer pubsub.Close()

	ch := pubsub.Channel()

	for msg := range ch {
		// Parse the metric payload
		var payload model.MetricPayload
		if err := json.Unmarshal([]byte(msg.Payload), &payload); err != nil {
			h.logger.Error("Failed to parse metric payload", zap.Error(err))
			continue
		}

		// Filter metrics based on subscription
		filteredMetrics := h.filterMetrics(client, payload.Metrics)
		if len(filteredMetrics) == 0 {
			continue
		}

		// Send to client
		filteredPayload := model.MetricPayload{Metrics: filteredMetrics}
		data, err := json.Marshal(model.WebSocketMessage{
			Type:    "metric",
			Payload: filteredPayload,
		})
		if err != nil {
			h.logger.Error("Failed to marshal message", zap.Error(err))
			continue
		}

		select {
		case client.send <- data:
		default:
			h.logger.Warn("Client send buffer full, dropping message")
		}
	}
}

// handleMessage handles incoming WebSocket messages
func (h *WebSocketHandler) handleMessage(client *Client, msg *model.WebSocketMessage) {
	switch msg.Type {
	case "subscribe":
		if payload, ok := msg.Payload.(map[string]interface{}); ok {
			if metricNames, ok := payload["metric_names"].([]interface{}); ok {
				client.mu.Lock()
				client.metricNames = make(map[string]bool)
				for _, name := range metricNames {
					if nameStr, ok := name.(string); ok {
						client.metricNames[nameStr] = true
					}
				}
				client.mu.Unlock()

				h.logger.Info("Client subscribed to metrics",
					zap.String("run_id", client.runID.String()),
					zap.Int("count", len(client.metricNames)))
			}
		}

	case "unsubscribe":
		client.mu.Lock()
		client.metricNames = make(map[string]bool)
		client.mu.Unlock()

		h.logger.Info("Client unsubscribed from all metrics",
			zap.String("run_id", client.runID.String()))
	}
}

// filterMetrics filters metrics based on client subscription
func (h *WebSocketHandler) filterMetrics(client *Client, metrics []model.Metric) []model.Metric {
	client.mu.RLock()
	defer client.mu.RUnlock()

	// If no filter, send all metrics
	if len(client.metricNames) == 0 {
		return metrics
	}

	var filtered []model.Metric
	for _, m := range metrics {
		if client.metricNames[m.MetricName] {
			filtered = append(filtered, m)
		}
	}
	return filtered
}
