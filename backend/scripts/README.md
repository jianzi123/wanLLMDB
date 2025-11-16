# wanLLMDB Database Management Scripts

This directory contains scripts for database backup, restore, and maintenance operations.

## Scripts

### 1. backup-database.sh

Creates a compressed backup of the PostgreSQL database.

**Features:**
- Compressed backups (gzip)
- Optional S3/MinIO upload
- Automatic cleanup of old backups
- Metadata file generation
- Configurable retention period

**Usage:**

```bash
# Basic local backup
./backup-database.sh

# Local backup only (skip S3 upload)
./backup-database.sh --local-only

# Custom retention period (14 days)
./backup-database.sh --retention 14

# Help
./backup-database.sh --help
```

**Environment Variables:**

```bash
# Required
POSTGRES_PASSWORD=your_database_password

# Optional (with defaults)
POSTGRES_DB=wanllmdb
POSTGRES_USER=wanllm
DB_HOST=localhost
DB_PORT=5432
BACKUP_DIR=./backups
BACKUP_RETENTION_DAYS=7

# For S3/MinIO upload
MINIO_BUCKET_NAME=wanllmdb-backups
MINIO_ENDPOINT=minio.example.com:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
```

**Example Output:**

```
[2025-01-16 12:00:00] Starting database backup...
[2025-01-16 12:00:00] Database: wanllmdb@localhost:5432
[2025-01-16 12:00:00] Backup file: ./backups/wanllmdb_backup_20250116_120000.sql.gz
[2025-01-16 12:00:00] Creating database dump...
[2025-01-16 12:00:05] ✓ Database backup created successfully
[2025-01-16 12:00:05] Backup size: 15M
[2025-01-16 12:00:05] ✓ Metadata file created
[2025-01-16 12:00:05] Uploading backup to S3...
[2025-01-16 12:00:10] ✓ Backup uploaded to S3
[2025-01-16 12:00:10] ✓ Backup completed successfully
```

---

### 2. restore-database.sh

Restores a PostgreSQL database from a backup file.

**Features:**
- Restore from local or S3/MinIO backup
- Automatic pre-restore backup creation
- Database verification after restore
- Automatic migration execution
- Safety confirmation prompt

**Usage:**

```bash
# Restore from local backup
./restore-database.sh wanllmdb_backup_20250116_120000.sql.gz

# Restore from S3 backup
./restore-database.sh wanllmdb_backup_20250116_120000.sql.gz --from-s3

# Force restore without confirmation (DANGEROUS)
./restore-database.sh wanllmdb_backup_20250116_120000.sql.gz --force

# Help
./restore-database.sh --help
```

**Environment Variables:**

Same as backup-database.sh

**Example Output:**

```
[2025-01-16 12:30:00] Found backup file: ./backups/wanllmdb_backup_20250116_120000.sql.gz
[2025-01-16 12:30:00] Backup size: 15M

⚠️  WARNING: This will DROP and RECREATE the database!
⚠️  All existing data will be LOST!

Database: wanllmdb@localhost:5432
Backup:   wanllmdb_backup_20250116_120000.sql.gz

Are you sure you want to continue? (type 'yes' to confirm): yes

[2025-01-16 12:30:05] Creating pre-restore backup...
[2025-01-16 12:30:10] ✓ Pre-restore backup created
[2025-01-16 12:30:10] Starting database restore...
[2025-01-16 12:30:30] ✓ Database restored successfully
[2025-01-16 12:30:30] Running database migrations...
[2025-01-16 12:30:35] ✓ Database migrations completed
[2025-01-16 12:30:35] Verifying restored database...
[2025-01-16 12:30:36] Tables found: 15
[2025-01-16 12:30:36] ✓ Restore completed successfully
```

---

## Automated Backups with Cron

To schedule automated backups, add a cron job:

```bash
# Edit crontab
crontab -e

# Add daily backup at 2:00 AM
0 2 * * * /opt/wanllmdb/backend/scripts/backup-database.sh >> /var/log/wanllmdb/backup.log 2>&1

# Add hourly backup (weekdays only)
0 * * * 1-5 /opt/wanllmdb/backend/scripts/backup-database.sh --local-only >> /var/log/wanllmdb/backup.log 2>&1

# Add weekly backup to S3 (Sundays at 3:00 AM)
0 3 * * 0 /opt/wanllmdb/backend/scripts/backup-database.sh >> /var/log/wanllmdb/backup.log 2>&1
```

**Cron Schedule Examples:**

- `0 2 * * *` - Daily at 2:00 AM
- `0 */6 * * *` - Every 6 hours
- `0 2 * * 0` - Weekly on Sunday at 2:00 AM
- `0 2 1 * *` - Monthly on the 1st at 2:00 AM

---

## Systemd Timer (Alternative to Cron)

For systemd-based systems, you can use a timer instead of cron.

**Create timer service:**

```bash
# /etc/systemd/system/wanllmdb-backup.service
[Unit]
Description=wanLLMDB Database Backup
After=network.target postgresql.service

[Service]
Type=oneshot
User=wanllm
WorkingDirectory=/opt/wanllmdb/backend/scripts
ExecStart=/opt/wanllmdb/backend/scripts/backup-database.sh
StandardOutput=append:/var/log/wanllmdb/backup.log
StandardError=append:/var/log/wanllmdb/backup.log
```

```bash
# /etc/systemd/system/wanllmdb-backup.timer
[Unit]
Description=wanLLMDB Daily Backup Timer
Requires=wanllmdb-backup.service

[Timer]
OnCalendar=daily
OnCalendar=02:00
Persistent=true

[Install]
WantedBy=timers.target
```

**Enable and start timer:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable wanllmdb-backup.timer
sudo systemctl start wanllmdb-backup.timer

# Check timer status
sudo systemctl status wanllmdb-backup.timer
sudo systemctl list-timers wanllmdb-backup.timer
```

---

## S3/MinIO Setup

To enable S3/MinIO backups, you need either AWS CLI or MinIO client installed.

### Option 1: AWS CLI

```bash
# Install AWS CLI
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# Verify installation
aws --version
```

### Option 2: MinIO Client

```bash
# Install MinIO client
wget https://dl.min.io/client/mc/release/linux-amd64/mc
chmod +x mc
sudo mv mc /usr/local/bin/

# Verify installation
mc --version
```

---

## Backup Best Practices

1. **Test Restores Regularly**
   - Verify backups can be restored
   - Test restore process in staging environment
   - Document restore procedures

2. **Multiple Retention Policies**
   - Daily backups: Keep 7 days
   - Weekly backups: Keep 4 weeks
   - Monthly backups: Keep 12 months

3. **Off-Site Storage**
   - Always upload critical backups to S3/MinIO
   - Consider multi-region replication
   - Test S3 restore process

4. **Monitoring**
   - Monitor backup job success/failure
   - Alert on backup failures
   - Track backup sizes over time

5. **Security**
   - Encrypt backups at rest (S3 encryption)
   - Encrypt backups in transit (HTTPS)
   - Restrict access to backup files
   - Regularly rotate S3 credentials

6. **Documentation**
   - Document restore procedures
   - Maintain runbook for disaster recovery
   - Keep contact information updated

---

## Troubleshooting

### Backup fails with "pg_dump: command not found"

Install PostgreSQL client tools:

```bash
# Ubuntu/Debian
sudo apt-get install postgresql-client

# RHEL/CentOS
sudo yum install postgresql

# macOS
brew install postgresql
```

### Backup fails with "PGPASSWORD not set"

Set the `POSTGRES_PASSWORD` environment variable:

```bash
export POSTGRES_PASSWORD=your_password
./backup-database.sh
```

Or add it to `.env` file in the parent directory.

### S3 upload fails

1. Check S3 credentials are correct
2. Verify S3 endpoint is accessible
3. Check bucket exists and you have write permissions
4. Verify AWS CLI or MinIO client is installed

### Restore fails with permission errors

Ensure the database user has sufficient privileges:

```sql
-- As postgres superuser
GRANT ALL PRIVILEGES ON DATABASE wanllmdb TO wanllm;
GRANT ALL ON SCHEMA public TO wanllm;
```

---

## Advanced Usage

### Backup to Multiple Locations

```bash
# Backup to local and S3
./backup-database.sh

# Backup to local only, then manually copy to multiple S3 buckets
./backup-database.sh --local-only
aws s3 cp backups/wanllmdb_backup_*.sql.gz s3://bucket1/
aws s3 cp backups/wanllmdb_backup_*.sql.gz s3://bucket2/
```

### Compress Older Backups

```bash
# Find backups older than 30 days and re-compress with higher compression
find backups/ -name "*.sql.gz" -mtime +30 -exec gzip -9 {} \;
```

### List Available Backups

```bash
# List local backups
ls -lh backups/wanllmdb_backup_*.sql.gz

# List S3 backups
aws s3 ls s3://wanllmdb-backups/backups/

# List with MinIO client
mc ls wanllmdb/wanllmdb-backups/backups/
```

---

## Support

For issues or questions, refer to:
- Main documentation: `PRODUCTION_DEPLOYMENT.md`
- Security documentation: `SECURITY_FIXES_IMPLEMENTED.md`
- Testing documentation: `TESTING.md`
