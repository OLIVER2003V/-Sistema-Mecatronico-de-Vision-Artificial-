/**
 * SORT-MATIC · Capturador de pantallas reales
 * Toma screenshots de todas las secciones del sistema desplegado
 * y las guarda en docs/assets/img/ listas para el manual.
 *
 * Uso: node capturar.mjs
 */

import { chromium } from 'playwright';
import { existsSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const IMG_DIR = resolve(__dirname, '../docs/assets/img');
const BASE_URL = 'https://sortmatic-botellas.duckdns.org';

// Crear directorio de imágenes si no existe
if (!existsSync(IMG_DIR)) mkdirSync(IMG_DIR, { recursive: true });

// ── Credenciales ──────────────────────────────────────────────
const CREDS = {
  admin:      { username: 'admin',      password: '123456' },
  supervisor: { username: 'supervisor', password: '123456' },
  operador:   { username: 'operador',   password: '123456' },
};

// ── Lista de capturas a tomar ──────────────────────────────────
const CAPTURAS = [
  // LOGIN
  { nombre: 'login-screen',         rol: null,         url: '/entrar',      desc: 'Pantalla de Login' },

  // CON ROL OPERADOR (pantalla mínima)
  { nombre: 'scada-dashboard',      rol: 'operador',   url: '/monitoreo',   desc: 'SCADA Dashboard completo (Operador)', fullPage: false },
  { nombre: 'scada-control-panel',  rol: 'operador',   url: '/monitoreo',   desc: 'Panel Control Faja', selector: '[class*="Control"]', clip: true },
  { nombre: 'contadores-linea',     rol: 'operador',   url: '/monitoreo',   desc: 'Contadores en tiempo real' },

  // CON ROL SUPERVISOR (analíticos, lotes, mermas, parámetros)
  { nombre: 'analiticos-dashboard', rol: 'supervisor', url: '/analiticos',  desc: 'Analíticos y KPIs completo' },
  { nombre: 'kpi-grid',             rol: 'supervisor', url: '/analiticos',  desc: 'KPI Grid' },
  { nombre: 'pareto-defectos',      rol: 'supervisor', url: '/analiticos',  desc: 'Pareto de Defectos' },
  { nombre: 'trend-chart',          rol: 'supervisor', url: '/analiticos',  desc: 'Gráfico de Tendencia' },
  { nombre: 'lotes-screen',         rol: 'supervisor', url: '/lotes',       desc: 'Gestión de Lotes' },
  { nombre: 'mermas-gallery',       rol: 'supervisor', url: '/mermas',      desc: 'Galería de Mermas' },
  { nombre: 'mermas-filtros',       rol: 'supervisor', url: '/mermas',      desc: 'Filtros de Mermas' },
  { nombre: 'parametros-screen',    rol: 'supervisor', url: '/parametros',  desc: 'Parámetros de Inspección' },
  { nombre: 'parametros-sliders',   rol: 'supervisor', url: '/parametros',  desc: 'Deslizadores de Confianza' },

  // CON ROL ADMIN (usuarios, auditoría)
  { nombre: 'usuarios-screen',      rol: 'admin',      url: '/usuarios',    desc: 'Gestión de Usuarios' },
  { nombre: 'auditoria-screen',     rol: 'admin',      url: '/auditoria',   desc: 'Bitácora de Auditoría' },
];

// ── Función principal ──────────────────────────────────────────
async function capturar() {
  console.log('\n🚀 SORT-MATIC · Capturador de pantallas reales');
  console.log('━'.repeat(55));

  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  // Sesiones por rol (reutilizamos contextos para no hacer login repetido)
  const sesiones = {};

  async function getSesion(rol) {
    if (!rol) return browser.newPage();
    if (sesiones[rol]) return sesiones[rol];

    const ctx  = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();

    const cred = CREDS[rol];
    console.log(`\n🔐 Login con rol: ${rol}`);

    await page.goto(`${BASE_URL}/entrar`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1000);

    // Rellenar formulario de login
    await page.fill('input[name="username"], input[type="text"]', cred.username);
    await page.fill('input[name="password"], input[type="password"]', cred.password);
    await page.click('button[type="submit"]');

    await page.waitForURL(url => !url.includes('/entrar'), { timeout: 15000 });
    console.log(`   ✅ Sesión iniciada como ${cred.username}`);

    sesiones[rol] = page;
    return page;
  }

  let ok = 0, fail = 0;

  for (const cap of CAPTURAS) {
    const destino = resolve(IMG_DIR, `${cap.nombre}.jpg`);
    console.log(`\n📸 ${cap.desc}`);
    console.log(`   → ${cap.url}  →  img/${cap.nombre}.jpg`);

    try {
      let page;
      if (!cap.rol) {
        // Sin login (pantalla de login)
        const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
        page = await ctx.newPage();
      } else {
        page = await getSesion(cap.rol);
      }

      await page.goto(`${BASE_URL}${cap.url}`, { waitUntil: 'networkidle', timeout: 30000 });
      // Esperar que carguen los datos (WebSocket / fetch)
      await page.waitForTimeout(2500);

      // Ocultar scrollbars para capturas más limpias
      await page.addStyleTag({ content: '::-webkit-scrollbar { display: none !important; }' });

      // Captura full-page o viewport
      await page.screenshot({
        path: destino,
        type: 'jpeg',
        quality: 92,
        fullPage: cap.fullPage !== false,
      });

      console.log(`   ✅ Guardado (${Math.round((await import('fs')).statSync(destino).size / 1024)} KB)`);
      ok++;

      // Para el login, también capturamos solo la tarjeta del formulario
      if (cap.nombre === 'login-screen') {
        // Ya fue capturado, podemos cerrar el contexto
      }

    } catch (err) {
      console.error(`   ❌ Error: ${err.message}`);
      fail++;
    }
  }

  // Captura especial: abrir modal de merma (si hay alguna)
  try {
    console.log('\n📸 Modal detalle de merma');
    const page = await getSesion('supervisor');
    await page.goto(`${BASE_URL}/mermas`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(2000);

    // Click en la primera ficha de merma si existe
    const ficha = page.locator('button.group').first();
    if (await ficha.count() > 0) {
      await ficha.click();
      await page.waitForTimeout(1200);
      await page.screenshot({
        path: resolve(IMG_DIR, 'merma-modal-detalle.jpg'),
        type: 'jpeg', quality: 92
      });
      console.log('   ✅ Modal de merma capturado');
      ok++;
    } else {
      console.log('   ⚠️  Sin mermas disponibles para el modal');
    }
  } catch (e) {
    console.log('   ⚠️  No se pudo capturar el modal:', e.message);
  }

  // Captura especial: menú de usuario (para mostrar Cambiar contraseña)
  try {
    console.log('\n📸 Menú de usuario (cambiar contraseña)');
    const page = await getSesion('operador');
    await page.goto(`${BASE_URL}/monitoreo`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(1500);
    // Abrir menú de usuario (botón con iniciales en la cabecera)
    const menuBtn = page.locator('header button[aria-haspopup]').first();
    if (await menuBtn.count() > 0) {
      await menuBtn.click();
      await page.waitForTimeout(600);
      await page.screenshot({
        path: resolve(IMG_DIR, 'login-screen-menu.jpg'),
        type: 'jpeg', quality: 92
      });
      console.log('   ✅ Menú de usuario capturado');
      ok++;
    }
  } catch (e) {
    console.log('   ⚠️  Menú usuario:', e.message);
  }

  // Captura especial: feed de eventos (scroll down en monitoreo)
  try {
    console.log('\n📸 Feed de eventos en tiempo real');
    const page = await getSesion('operador');
    await page.goto(`${BASE_URL}/monitoreo`, { waitUntil: 'networkidle', timeout: 30000 });
    await page.waitForTimeout(3000);
    await page.screenshot({
      path: resolve(IMG_DIR, 'eventos-feed.jpg'),
      type: 'jpeg', quality: 92, fullPage: true
    });
    console.log('   ✅ Feed de eventos capturado');
    ok++;
  } catch (e) {
    console.log('   ⚠️  Feed eventos:', e.message);
  }

  await browser.close();

  console.log('\n' + '━'.repeat(55));
  console.log(`✅ Capturas exitosas: ${ok}`);
  console.log(`❌ Errores:          ${fail}`);
  console.log(`📁 Imágenes en:      docs/assets/img/`);
  console.log('━'.repeat(55));

  // Listar las imágenes generadas
  const { readdirSync, statSync } = await import('fs');
  const archivos = readdirSync(IMG_DIR);
  console.log('\nArchivos generados:');
  for (const f of archivos) {
    const size = Math.round(statSync(resolve(IMG_DIR, f)).size / 1024);
    console.log(`  ${f.padEnd(40)} ${size} KB`);
  }
}

capturar().catch(console.error);
