@echo off
REM Run intelligent VACUUM strategy (partition-aware)
psql --no-password -h localhost -U postgres -d pump_station_optimization -v ON_ERROR_STOP=1 -c "SELECT smart_vacuum_strategy();"
exit /b %errorlevel%
