import { config } from '../server/config.js';
import { hashPassword } from '../server/lib/auth.js';
import { initializeDatabase, seedWorkshops, one, query, pool } from '../server/db/database.js';

async function run() {
  await initializeDatabase();
  await seedWorkshops();
  const admin = await one('SELECT id FROM admins WHERE email = $1', [config.adminEmail]);
  if (!admin) {
    await query('INSERT INTO admins (email, password_hash, name) VALUES ($1, $2, $3)', [config.adminEmail, hashPassword(config.adminPassword), 'Rara Wulandari']);
    console.log(`Admin dibuat: ${config.adminEmail}`);
  } else {
    console.log(`Admin sudah ada: ${config.adminEmail}`);
  }
  const workshops = await one('SELECT COUNT(*)::int AS count FROM workshops');
  console.log(`Total workshop di database: ${workshops.count}`);
  await pool.end();
}

run().catch((error) => {
  console.error('Seeding gagal:', error.message);
  process.exit(1);
});
