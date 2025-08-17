@echo off
REM Run a pg_stat_statements snapshot and cleanup old rows
psql --no-password -h localhost -U postgres -d pump_station_optimization -v ON_ERROR_STOP=1 -c "SELECT monitoring.capture_pgss_snapshot(); SELECT monitoring.cleanup_pgss_snapshot();"
exit /b %errorlevel%
