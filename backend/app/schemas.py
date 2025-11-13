from app import ma
from app.models import PowerPlant, State, Sector, EnergyType, ProductionLog, OperationalStatus, RegionDetails

# PowerPlant Schema
class PowerPlantSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PowerPlant
        include_fk = True
        load_instance = True
    
    state = ma.Nested('StateSchema', only=['State_Name', 'Region'])
    sector = ma.Nested('SectorSchema')
    energy_type = ma.Nested('EnergyTypeSchema')

# State Schema
class StateSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = State
        load_instance = True

# Sector Schema
class SectorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Sector
        load_instance = True

# EnergyType Schema
class EnergyTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = EnergyType
        load_instance = True

# ProductionLog Schema
class ProductionLogSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProductionLog
        load_instance = True
    
    plant = ma.Nested('PowerPlantSchema', only=['Plant_Name'])

# OperationalStatus Schema
class OperationalStatusSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = OperationalStatus
        load_instance = True
    
    plant = ma.Nested('PowerPlantSchema', only=['Plant_Name', 'State_Code'])

# RegionDetails Schema
class RegionDetailsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = RegionDetails
        load_instance = True
    
    state = ma.Nested('StateSchema', only=['State_Name', 'Region'])

# Initialize schema instances for use in routes
powerplant_schema = PowerPlantSchema()
powerplants_schema = PowerPlantSchema(many=True)

state_schema = StateSchema()
states_schema = StateSchema(many=True)

sector_schema = SectorSchema()
sectors_schema = SectorSchema(many=True)

energytype_schema = EnergyTypeSchema()
energytypes_schema = EnergyTypeSchema(many=True)

productionlog_schema = ProductionLogSchema()
productionlogs_schema = ProductionLogSchema(many=True)

operationalstatus_schema = OperationalStatusSchema()
operationalstatuses_schema = OperationalStatusSchema(many=True)

regiondetails_schema = RegionDetailsSchema()
regiondetails_list_schema = RegionDetailsSchema(many=True)
