@echo off
set PGPASSWORD=q5707073
psql -h localhost -U postgres -d pump_station_optimization -f scripts/verify_tables.sql
