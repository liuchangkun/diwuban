@echo off
REM Refresh hourly materialized view (prefer concurrently)
psql --no-password -h localhost -U postgres -d pump_station_optimization -v ON_ERROR_STOP=1 -c "REFRESH MATERIALIZED VIEW CONCURRENTLY reporting.mv_measurements_hourly;"
exit /b %errorlevel%
