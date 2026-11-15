"""Cloud runtime: allow bounded ffprobe + ffmpeg playback work to finish."""
import os
bind = '0.0.0.0:' + os.getenv('PORT', '8080')
workers = int(os.getenv('WEB_CONCURRENCY', '2'))
threads = 1
timeout = 240
graceful_timeout = 240
accesslog = '-'
errorlog = '-'
# ProxyFix is the single explicitly configured authority for forwarding headers.
forwarded_allow_ips = ''
