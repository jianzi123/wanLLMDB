package config

import (
	"fmt"
	"os"
	"strconv"
)

type Config struct {
	Port          int
	Environment   string
	TimescaleURL  string
	RedisURL      string
	BatchSize     int
	CacheTimeout  int
}

func Load() (*Config, error) {
	cfg := &Config{
		Port:         getEnvAsInt("PORT", 8001),
		Environment:  getEnv("ENVIRONMENT", "development"),
		TimescaleURL: getEnv("TIMESCALE_URL", "postgresql://wanllmdb:password@localhost:5433/wanllmdb_metrics"),
		RedisURL:     getEnv("REDIS_URL", "redis://localhost:6379/0"),
		BatchSize:    getEnvAsInt("BATCH_SIZE", 1000),
		CacheTimeout: getEnvAsInt("CACHE_TIMEOUT", 300),
	}

	if err := cfg.validate(); err != nil {
		return nil, fmt.Errorf("invalid configuration: %w", err)
	}

	return cfg, nil
}

func (c *Config) validate() error {
	if c.TimescaleURL == "" {
		return fmt.Errorf("TIMESCALE_URL is required")
	}
	if c.RedisURL == "" {
		return fmt.Errorf("REDIS_URL is required")
	}
	if c.Port <= 0 || c.Port > 65535 {
		return fmt.Errorf("invalid port: %d", c.Port)
	}
	return nil
}

func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func getEnvAsInt(key string, defaultValue int) int {
	if value := os.Getenv(key); value != "" {
		if intValue, err := strconv.Atoi(value); err == nil {
			return intValue
		}
	}
	return defaultValue
}
