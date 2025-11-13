UPDATE REGION_DETAILS
SET Grid_Frequency_Hz = 60.00;

CALL sp_UpdateRegionGenerationFromProduction();

CALL sp_UpdateRegionSurplusAndImports();

CALL sp_CalculatePlantEfficiency();

CALL sp_InsertAllMissingActiveStatuses();
