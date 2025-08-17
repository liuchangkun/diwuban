@echo off
REM Refresh daily materialized view (prefer concurrently)
psql --no-password -h localhost -U postgres -d pump_station_optimization -v ON_ERROR_STOP=1 -c "REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_measurements_daily;"
exit /b %errorlevel%
