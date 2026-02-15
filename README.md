# 🛡️ S3-Guardian

Automated Docker volume backups to S3-compatible storage (AWS S3, Cloudflare R2, Backblaze B2, etc.)

[![Docker Pulls](https://img.shields.io/docker/pulls/nexnghxsst/seguardia)](https://ghcr.io/nexnghxsst/seguardia)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Stars](https://img.shields.io/github/stars/nexnghxsst/s3-guardian)](https://github.com/nexnghxsst/s3-guardian)

## ✨ Features

- 🔄 Automatic scheduled backups
- ☁️ Works with any S3-compatible storage
- 📦 Smart compression (tar.gz)
- 🧹 Automatic retention management
- 🐳 Sidecar pattern - non-invasive
- 🔒 Secure (read-only mounts)
- 🚀 Zero configuration needed

## 🚀 Quick Start
```yaml
version: '3.8'

services:
  your-app:
    image: your-app:latest
    volumes:
      - app_data:/data

  s3-guardian:
    image: ghcr.io/nexnghxsst/seguardia:latest
    environment:
      AWS_ACCESS_KEY_ID: ${AWS_ACCESS_KEY_ID}
      AWS_SECRET_ACCESS_KEY: ${AWS_SECRET_ACCESS_KEY}
      S3_BUCKET: my-backups
      S3_ENDPOINT_URL: https://your-account.r2.cloudflarestorage.com
      TARGET_PATH: /data
      BACKUP_INTERVAL: 6h
    volumes:
      - app_data:/data:ro
    restart: unless-stopped

volumes:
  app_data:
```

## 📖 Documentation

- [Installation Guide](INSTALL.md)
- [Configuration Options](#configuration)
- [Examples](#examples)

## ⚙️ Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AWS_ACCESS_KEY_ID` | ✅ | - | S3 access key |
| `AWS_SECRET_ACCESS_KEY` | ✅ | - | S3 secret key |
| `S3_BUCKET` | ✅ | - | Bucket name |
| `S3_ENDPOINT_URL` | ❌ | - | For R2/B2/MinIO |
| `TARGET_PATH` | ✅ | - | Path to backup |
| `BACKUP_INTERVAL` | ❌ | `6h` | Frequency |
| `RETENTION_DAYS` | ❌ | `30` | Days to keep |

## 📚 Examples

### Minecraft Server
```yaml
s3-guardian:
  image: ghcr.io/nexnghxsst/seguardia:latest
  environment:
    S3_BUCKET: minecraft-backups
    TARGET_PATH: /data
    BACKUP_INTERVAL: 6h
  volumes:
    - minecraft_data:/data:ro
```

### PostgreSQL Database
```yaml
s3-guardian:
  image: ghcr.io/nexnghxsst/seguardia:latest
  environment:
    S3_BUCKET: db-backups
    TARGET_PATH: /var/lib/postgresql/data
    BACKUP_INTERVAL: 12h
    RETENTION_DAYS: 90
  volumes:
    - postgres_data:/var/lib/postgresql/data:ro
```

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

## 📄 License

MIT License - see [LICENSE](LICENSE.md)

## 🙏 Support

- 🐛 [Report Issues](https://github.com/nexnghxsst/s3-guardian/issues)
- 💬 [Discussions](https://github.com/nexnghxsst/s3-guardian/discussions)
- ⭐ Star this repo if you find it useful!

---

Made with love for reliable backups!
