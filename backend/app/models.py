from app import db, ma
from datetime import datetime

class PowerPlant(db.Model):
    __tablename__ = 'POWERPLANTS'

    Plant_ID = db.Column(db.String(20), primary_key=True)
    Plant_Name = db.Column(db.String(255), nullable=False)
    State_Code = db.Column(db.String(10), db.ForeignKey('STATE.State_Code'))
    Sector_ID = db.Column(db.String(10), db.ForeignKey('SECTOR.Sector_ID'))
    Type_ID = db.Column(db.String(10), db.ForeignKey('ENERGYTYPE.Type_ID'))

    # Relationships
    state = db.relationship('State', backref='powerplants')
    sector = db.relationship('Sector', backref='powerplants')
    energy_type = db.relationship('EnergyType', backref='powerplants')
    production_logs = db.relationship('ProductionLog', backref='plant', lazy='dynamic')
    operational_status = db.relationship('OperationalStatus', backref='plant', lazy='dynamic')

class State(db.Model):
    __tablename__ = 'STATE'

    State_Code = db.Column(db.String(10), primary_key=True)
    State_Name = db.Column(db.String(100))
    Region = db.Column(db.String(100))
    Population = db.Column(db.BigInteger)

class Sector(db.Model):
    __tablename__ = 'SECTOR'

    Sector_ID = db.Column(db.String(10), primary_key=True)
    Sector_Name = db.Column(db.String(100), nullable=False)

class EnergyType(db.Model):
    __tablename__ = 'ENERGYTYPE'

    Type_ID = db.Column(db.String(10), primary_key=True)
    Type_Name = db.Column(db.String(100))
    Description = db.Column(db.Text)

class ProductionLog(db.Model):
    __tablename__ = 'PRODUCTIONLOG'

    Plant_ID = db.Column(db.String(20), db.ForeignKey('POWERPLANTS.Plant_ID'), primary_key=True)
    Log_Date = db.Column(db.Date, primary_key=True)
    Efficiency_Percentage = db.Column(db.Numeric(5, 2))
    Todays_Actual_MU = db.Column(db.Numeric(12, 2))
    Capable_Generation_MU = db.Column(db.Numeric(12, 2))
    Operational_Capacity_MW = db.Column(db.Numeric(10, 2))
    Coal_Stock_Days = db.Column(db.Numeric(10, 2))

class OperationalStatus(db.Model):
    __tablename__ = 'OPERATIONAL_STATUS'

    Plant_ID = db.Column(db.String(20), db.ForeignKey('POWERPLANTS.Plant_ID'), primary_key=True)
    Unit_Number = db.Column(db.String(20), primary_key=True)
    Status_Date = db.Column(db.Date, primary_key=True)
    Cap_Under_Outage_MW = db.Column(db.Numeric(10, 2))
    Status = db.Column(db.Enum('Active', 'Under Outage', 'Not Commisioned'))
    Outage_Date = db.Column(db.Date)
    Expected_Sync_Date = db.Column(db.Date)
    Remarks = db.Column(db.Text)

class RegionDetails(db.Model):
    __tablename__ = 'REGION_DETAILS'

    State_Code = db.Column(db.String(10), db.ForeignKey('STATE.State_Code'), primary_key=True)
    Report_Date = db.Column(db.Date, primary_key=True)
    Generated_MU = db.Column(db.Numeric(12, 2))
    Imported_MU = db.Column(db.Numeric(12, 2))
    Surplus_MU = db.Column(db.Numeric(12, 2))
    Demand_MU = db.Column(db.Numeric(12, 2))
    Monitored_Capacity_MW = db.Column(db.Numeric(10, 2))
    Grid_Frequency_HZ = db.Column(db.Numeric(5, 2))

# Marshmallow Schemas for serialization
class PowerPlantSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = PowerPlant
        include_fk = True

    state = ma.Nested('StateSchema', only=['State_Name', 'Region'])
    sector = ma.Nested('SectorSchema')
    energy_type = ma.Nested('EnergyTypeSchema')

class StateSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = State

class SectorSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = Sector

class EnergyTypeSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = EnergyType

class ProductionLogSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ProductionLog

class RegionDetailsSchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = RegionDetails
