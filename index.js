// ...existing code...
const port = 8000;
const express = require("express");
const app = express();
const mongoose = require("mongoose");
const cors = require("cors");
const path = require("path");
// MySQL client (promise)
const mysql = require('mysql2/promise');

app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cors());

//Connection
mongoose
  .connect("mongodb://localhost:27017/IndianEnergy-Company")
  .then(() => console.log("MongoDB Connected"))
  .catch((err) => console.error("Mongo Error:", err));

// MySQL pool 
const MYSQL_HOST = process.env.MYSQL_HOST || '127.0.0.1';
const MYSQL_PORT = process.env.MYSQL_PORT ? Number(process.env.MYSQL_PORT) : 3306;
const MYSQL_USER = process.env.MYSQL_USER || 'root';
const MYSQL_PASSWORD = process.env.MYSQL_PASSWORD || 'root123';
const MYSQL_DB = process.env.MYSQL_DB || 'IndianEnergyDB';
const INSERT_IF_MISSING = (process.env.INSERT_IF_MISSING === '1');

let mysqlPool;
async function initMysqlPool() {
  if (!mysqlPool) {
    mysqlPool = await mysql.createPool({
      host: MYSQL_HOST,
      port: MYSQL_PORT,
      user: MYSQL_USER,
      password: MYSQL_PASSWORD,
      database: MYSQL_DB,
      waitForConnections: true,
      connectionLimit: 10,
      queueLimit: 0,
    });
  }
  return mysqlPool;
}

//  (transaction must be held by caller via connection)
async function applyDemandTx(conn, stateCode, reportDate, demandMU, insertIfMissing = false) {
  // conn is a mysql2 connection with transaction started
  const TARGET_TABLE = process.env.TARGET_TABLE || 'REGION_DETAILS';
  const TARGET_STATE_COL = process.env.TARGET_STATE_COL || 'State_Code';
  const TARGET_DATE_COL = process.env.TARGET_DATE_COL || 'Report_Date';
  const TARGET_DEMAND_COL = process.env.TARGET_DEMAND_COL || 'Demand_MU';

  // SELECT FOR UPDATE
  const [rows] = await conn.execute(
    `SELECT ${TARGET_DEMAND_COL} FROM ${TARGET_TABLE} WHERE ${TARGET_STATE_COL} = ? AND ${TARGET_DATE_COL} = ? FOR UPDATE`,
    [stateCode, reportDate]
  );

  if (rows.length) {
    const current = Number(rows[0][TARGET_DEMAND_COL] || 0);
    const newVal = current + Number(demandMU || 0);
    await conn.execute(
      `UPDATE ${TARGET_TABLE} SET ${TARGET_DEMAND_COL} = ? WHERE ${TARGET_STATE_COL} = ? AND ${TARGET_DATE_COL} = ?`,
      [newVal, stateCode, reportDate]
    );
    return { applied: true };
  }

  if (insertIfMissing) {
    
    await conn.execute(
      `INSERT INTO ${TARGET_TABLE} (${TARGET_STATE_COL}, ${TARGET_DATE_COL}, ${TARGET_DEMAND_COL}) VALUES (?, ?, ?)`,
      [stateCode, reportDate, Number(demandMU || 0)]
    );
    return { applied: true, inserted: true };
  }

  return { applied: false, reason: 'no_target_row' };
}

// Helper: subtract demand in transaction (for rollback)
async function subtractDemandTx(conn, stateCode, reportDate, demandMU) {
  const TARGET_TABLE = process.env.TARGET_TABLE || 'REGION_DETAILS';
  const TARGET_STATE_COL = process.env.TARGET_STATE_COL || 'State_Code';
  const TARGET_DATE_COL = process.env.TARGET_DATE_COL || 'Report_Date';
  const TARGET_DEMAND_COL = process.env.TARGET_DEMAND_COL || 'Demand_MU';

  const [rows] = await conn.execute(
    `SELECT ${TARGET_DEMAND_COL} FROM ${TARGET_TABLE} WHERE ${TARGET_STATE_COL} = ? AND ${TARGET_DATE_COL} = ? FOR UPDATE`,
    [stateCode, reportDate]
  );
  if (!rows.length) return { ok: false, reason: 'no_target_row' };
  const current = Number(rows[0][TARGET_DEMAND_COL] || 0);
  let newVal = current - Number(demandMU || 0);
  if (newVal < 0) newVal = 0;
  await conn.execute(
    `UPDATE ${TARGET_TABLE} SET ${TARGET_DEMAND_COL} = ? WHERE ${TARGET_STATE_COL} = ? AND ${TARGET_DATE_COL} = ?`,
    [newVal, stateCode, reportDate]
  );
  return { ok: true };
}

app.get("/", (req, res) => {
  res.send("Express is running");
});

const CompanySchema = new mongoose.Schema(
  {
    id: { type: Number, required: true, unique: true },
    company_name: { type: String, required: true },
    company_description: { type: String },
    company_email: { type: String },
    demand_date: { type: String, required: true },
    demand_MU: { type: Number, required: true },
    state_code: { type: String, required: true },
    // sync metadata
    synced: { type: Boolean, default: false },
    applied_at: { type: Date },
    rolled_back_at: { type: Date },
  },
  { timestamps: true }
);

const Company = mongoose.model("Company", CompanySchema);

// Create company
app.post("/companies", async (req, res) => {
  const body = req.body;

  if (
    !body ||
    body.id == null ||
    !body.company_name ||
    !body.demand_date ||
    body.demand_MU == null ||
    !body.state_code
  ) {
    return res.status(400).json({ msg: "Required fields missing" });
  }

  try {
    // We'll attempt to apply the REGION_DETAILS update inside a MySQL transaction
    const pool = await initMysqlPool();
    const conn = await pool.getConnection();
    try {
      await conn.beginTransaction();
      // attempt update/insert in REGION_DETAILS (transactional)
      const applyRes = await applyDemandTx(conn, body.state_code, body.demand_date, body.demand_MU, INSERT_IF_MISSING);
      if (!applyRes.applied) {
        // nothing applied and not allowed to insert - rollback and return error
        await conn.rollback();
        return res.status(400).json({ msg: 'No REGION_DETAILS row for given state/date and insert-if-missing is false' });
      }

      // Create company in Mongo. create with synced:false; we'll set synced=true after MySQL commit
      const result = await Company.create({
        id: body.id,
        company_name: body.company_name,
        company_description: body.company_description || "",
        company_email: body.company_email || "",
        demand_date: body.demand_date,
        demand_MU: body.demand_MU,
        state_code: body.state_code,
      });

      // Call stored procedure to refresh imports/surplus within the same transaction
      try {
        await conn.execute('CALL sp_UpdateRegionSurplusAndImports()');
      } catch (procErr) {
        // If the procedure fails, rollback and return error
        try { await conn.rollback(); } catch(e){}
        console.error('Stored procedure sp_UpdateRegionSurplusAndImports failed:', procErr);
        return res.status(500).json({ msg: 'Error running post-update procedure', error: procErr.message });
      }

      // Commit MySQL after Mongo create succeeded and procedure ran successfully
      await conn.commit();

      // mark mongo doc as synced (best-effort)
      try {
        await Company.updateOne({ id: body.id }, { $set: { synced: true, applied_at: new Date() } });
      } catch (uerr) {
        console.error('Failed to mark company as synced after commit:', uerr);
      }

      return res.status(201).json({ msg: "Success", company: result });
    } catch (err) {
      try { await conn.rollback(); } catch(e){}
      console.error('Error applying REGION_DETAILS or creating company:', err);
      // If Mongo create succeeded but commit failed, we attempted rollback; still surface error
      return res.status(500).json({ msg: "Error creating Company and applying REGION_DETAILS", error: err.message });
    } finally {
      try { conn.release(); } catch(e){}
    }
  } catch (err) {
    console.error(err);
    if (err.code === 11000) {
      return res.status(409).json({ msg: "Duplicate id" });
    }
    return res.status(500).json({ msg: "Error creating Company", error: err.message });
  }
});

// Get all companies
app.get("/companies", async (req, res) => {
  try {
    const companies = await Company.find({});
    return res.json(companies);
  } catch (err) {
    console.error(err);
    return res.status(500).json({ msg: "Error fetching companies" });
  }
});

app.patch("/companies/:id/demand", async (req, res) => {
  const id = Number(req.params.id);
  const { demand_MU } = req.body;

  if (demand_MU == null || isNaN(Number(demand_MU))) {
    return res.status(400).json({ msg: "Valid demand_MU is required" });
  }

  try {
    const updated = await Company.findOneAndUpdate(
      { id },
      { $set: { demand_MU: Number(demand_MU) } },
      { new: true, runValidators: true }
    );

    if (!updated) return res.status(404).json({ msg: "Company not found" });

    return res.json({ msg: "demand_MU updated", company: updated });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ msg: "Error updating demand_MU" });
  }
});

// Delete company by id (RESTful)
app.delete("/companies/:id", async (req, res) => {
  const id = Number(req.params.id);
  try {
    const company = await Company.findOne({ id });
    if (!company) return res.status(404).json({ msg: "Company not found" });

    // perform MySQL rollback (subtract demand) inside a transaction, then delete Mongo doc
    const pool = await initMysqlPool();
    const conn = await pool.getConnection();
    try {
      await conn.beginTransaction();
      const subRes = await subtractDemandTx(conn, company.state_code, company.demand_date, company.demand_MU);
      if (!subRes.ok) {
        await conn.rollback();
        return res.status(400).json({ msg: 'Failed to rollback REGION_DETAILS', reason: subRes.reason });
      }
      // Call stored procedure to refresh imports/surplus within the same transaction
      try {
        await conn.execute('CALL sp_UpdateRegionSurplusAndImports()');
      } catch (procErr) {
        try { await conn.rollback(); } catch(e){}
        console.error('Stored procedure sp_UpdateRegionSurplusAndImports failed during delete rollback:', procErr);
        return res.status(500).json({ msg: 'Error running post-rollback procedure', error: procErr.message });
      }

      await conn.commit();
    } catch (err) {
      try { await conn.rollback(); } catch(e){}
      console.error('Error during MySQL rollback for delete:', err);
      return res.status(500).json({ msg: 'Error rolling back REGION_DETAILS', error: err.message });
    } finally {
      try { conn.release(); } catch(e){}
    }

    // Now delete from Mongo
    const deleted = await Company.findOneAndDelete({ id });
    if (!deleted) return res.status(404).json({ msg: "Company not found (after rollback)" });
    return res.json({ success: true, deleted });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ msg: "Error deleting company" });
  }
});

app.listen(port, (error) => {
  if (!error) {
    console.log("Server is running at port " + port);
  } else {
    console.log("Error: " + error);
  }
});
