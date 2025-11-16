package main

import (
	"context"
	"fmt"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/gin-gonic/gin"
	"go.uber.org/zap"

	"github.com/wanllmdb/metric-service/internal/config"
	"github.com/wanllmdb/metric-service/internal/db"
	"github.com/wanllmdb/metric-service/internal/handler"
	"github.com/wanllmdb/metric-service/internal/repository"
	"github.com/wanllmdb/metric-service/internal/service"
)

func main() {
	// Initialize logger
	logger, err := zap.NewProduction()
	if err != nil {
		fmt.Printf("Failed to initialize logger: %v\n", err)
		os.Exit(1)
	}
	defer logger.Sync()

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		logger.Fatal("Failed to load configuration", zap.Error(err))
	}

	// Initialize database connection
	dbPool, err := db.NewPool(context.Background(), cfg.TimescaleURL)
	if err != nil {
		logger.Fatal("Failed to connect to database", zap.Error(err))
	}
	defer dbPool.Close()

	// Initialize Redis client
	redisClient := db.NewRedisClient(cfg.RedisURL)
	defer redisClient.Close()

	// Initialize repository
	metricRepo := repository.NewMetricRepository(dbPool, logger)

	// Initialize service
	metricService := service.NewMetricService(metricRepo, redisClient, logger)

	// Initialize handlers
	metricHandler := handler.NewMetricHandler(metricService, logger)
	wsHandler := handler.NewWebSocketHandler(metricService, logger)

	// Setup Gin router
	if cfg.Environment == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(corsMiddleware())
	router.Use(loggingMiddleware(logger))

	// Health check
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "healthy"})
	})

	// API routes
	v1 := router.Group("/api/v1")
	{
		// Metric endpoints
		v1.POST("/metrics/batch", metricHandler.BatchWrite)
		v1.GET("/runs/:run_id/metrics", metricHandler.GetRunMetrics)
		v1.GET("/runs/:run_id/metrics/:metric_name", metricHandler.GetMetricHistory)
		v1.GET("/runs/:run_id/metrics/:metric_name/latest", metricHandler.GetLatestMetric)
		v1.GET("/runs/:run_id/metrics/:metric_name/stats", metricHandler.GetMetricStats)

		// System metrics
		v1.POST("/metrics/system/batch", metricHandler.BatchWriteSystemMetrics)
		v1.GET("/runs/:run_id/system-metrics", metricHandler.GetSystemMetrics)
	}

	// WebSocket endpoint
	router.GET("/ws/metrics/:run_id", wsHandler.HandleConnection)

	// Start server
	srv := &http.Server{
		Addr:    fmt.Sprintf(":%d", cfg.Port),
		Handler: router,
	}

	// Graceful shutdown
	go func() {
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Fatal("Failed to start server", zap.Error(err))
		}
	}()

	logger.Info("Metric service started", zap.Int("port", cfg.Port))

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	logger.Info("Shutting down server...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		logger.Fatal("Server forced to shutdown", zap.Error(err))
	}

	logger.Info("Server exited")
}

func corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Writer.Header().Set("Access-Control-Allow-Origin", "*")
		c.Writer.Header().Set("Access-Control-Allow-Credentials", "true")
		c.Writer.Header().Set("Access-Control-Allow-Headers", "Content-Type, Content-Length, Accept-Encoding, X-CSRF-Token, Authorization, accept, origin, Cache-Control, X-Requested-With")
		c.Writer.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS, GET, PUT, DELETE")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

func loggingMiddleware(logger *zap.Logger) gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		query := c.Request.URL.RawQuery

		c.Next()

		latency := time.Since(start)
		logger.Info("HTTP request",
			zap.String("method", c.Request.Method),
			zap.String("path", path),
			zap.String("query", query),
			zap.Int("status", c.Writer.Status()),
			zap.Duration("latency", latency),
			zap.String("client_ip", c.ClientIP()),
		)
	}
}
