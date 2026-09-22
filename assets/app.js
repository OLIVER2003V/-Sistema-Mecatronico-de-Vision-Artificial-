/* ============================================================
   SORT-MATIC · Manual de Usuario — JavaScript
   Navegación SPA estática entre secciones
   ============================================================ */

(function () {
  'use strict';

  /* --- Elementos DOM --- */
  const sidebar  = document.getElementById('sidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  const menuBtn  = document.getElementById('menuBtn');
  const navLinks = document.querySelectorAll('.nav-link');
  const sections = document.querySelectorAll('.section');

  /* ============================================================
     NAVEGACIÓN SPA
     ============================================================ */
  function activateSection(target) {
    // Ocultar todas las secciones
    sections.forEach(s => s.classList.remove('active'));

    // Mostrar la sección destino
    const section = document.getElementById(target);
    if (section) {
      section.classList.add('active');
      // Scroll al inicio del contenido
      document.getElementById('mainContent').scrollTo({ top: 0, behavior: 'smooth' });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    // Actualizar links activos
    navLinks.forEach(link => {
      const linkTarget = link.getAttribute('data-section');
      if (linkTarget === target) {
        link.classList.add('active');
      } else {
        link.classList.remove('active');
      }
    });

    // Actualizar URL sin recargar (hash navigation)
    history.pushState(null, '', `#${target}`);

    // Cerrar sidebar en móvil
    closeSidebar();
  }

  /* Interceptar clicks en los nav-links */
  navLinks.forEach(link => {
    link.addEventListener('click', function (e) {
      e.preventDefault();
      const target = this.getAttribute('data-section');
      if (target) activateSection(target);
    });
  });

  /* Manejar navegación con botón atrás/adelante del navegador */
  window.addEventListener('popstate', function () {
    const hash = window.location.hash.replace('#', '');
    if (hash) activateSection(hash);
  });

  /* Cargar sección desde el hash al iniciar */
  function loadFromHash() {
    const hash = window.location.hash.replace('#', '');
    if (hash && document.getElementById(hash)) {
      activateSection(hash);
    } else {
      // Sección por defecto: introducción
      activateSection('introduccion');
    }
  }

  /* ============================================================
     SIDEBAR MÓVIL
     ============================================================ */
  function openSidebar() {
    sidebar.classList.add('open');
    overlay.classList.add('visible');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('open');
    overlay.classList.remove('visible');
    document.body.style.overflow = '';
  }

  if (menuBtn)  menuBtn.addEventListener('click', openSidebar);
  if (overlay)  overlay.addEventListener('click', closeSidebar);

  /* Cerrar sidebar con Escape */
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') closeSidebar();
  });

  /* ============================================================
     ANIMACIÓN DE SECCIONES
     ============================================================ */
  // Agregar clase de animación al activar
  const style = document.createElement('style');
  style.textContent = `
    .section.active {
      animation: fadeIn 0.2s ease forwards;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(6px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `;
  document.head.appendChild(style);

  /* ============================================================
     HIGHLIGHT DE CÓDIGO EN PLACEHOLDERS
     (Resaltar los tags de HTML en los bloques de código)
     ============================================================ */
  document.querySelectorAll('.img-placeholder-inner code').forEach(el => {
    const text = el.textContent;
    // Colorear etiquetas HTML básicas
    el.innerHTML = text
      .replace(/&lt;/g, '<span style="color:#a78bfa">&lt;</span>')
      .replace(/&gt;/g, '<span style="color:#a78bfa">&gt;</span>')
      .replace(/(src|alt|class)=/g, '<span style="color:#34d399">$1</span>=')
      .replace(/"([^"]+)"/g, '"<span style="color:#fbbf24">$1</span>"');
  });

  /* ============================================================
     BUSCADOR RÁPIDO DE SECCIONES (Ctrl+K)
     ============================================================ */
  const searchHtml = `
    <div id="searchModal" class="search-modal" style="display:none;" role="dialog" aria-label="Buscar sección">
      <div class="search-backdrop"></div>
      <div class="search-box">
        <input id="searchInput" type="text" placeholder="Buscar en el manual..." autocomplete="off" />
        <div id="searchResults" class="search-results"></div>
        <p class="search-hint"><kbd>↑</kbd><kbd>↓</kbd> navegar &nbsp; <kbd>Enter</kbd> abrir &nbsp; <kbd>Esc</kbd> cerrar</p>
      </div>
    </div>
  `;

  const searchStyle = `
    .search-modal { position: fixed; inset: 0; z-index: 100; display: flex; align-items: flex-start; justify-content: center; padding-top: 5rem; }
    .search-backdrop { position: absolute; inset: 0; background: rgba(2,6,23,0.8); }
    .search-box { position: relative; width: 100%; max-width: 520px; background: #1e293b; border: 1px solid #334155; border-radius: 0.875rem; overflow: hidden; box-shadow: 0 25px 50px rgba(0,0,0,0.5); margin: 0 1rem; }
    #searchInput { width: 100%; padding: 1rem 1.25rem; background: transparent; border: none; outline: none; color: #f1f5f9; font-size: 1rem; font-family: inherit; border-bottom: 1px solid #334155; }
    #searchInput::placeholder { color: #64748b; }
    .search-results { max-height: 320px; overflow-y: auto; }
    .search-result-item { padding: 0.75rem 1.25rem; cursor: pointer; display: flex; align-items: center; gap: 0.625rem; font-size: 0.9rem; color: #94a3b8; transition: background 0.1s; }
    .search-result-item:hover, .search-result-item.selected { background: rgba(34,211,238,0.08); color: #f1f5f9; }
    .search-result-item .result-icon { color: #22d3ee; flex-shrink: 0; }
    .search-no-results { padding: 2rem; text-align: center; color: #64748b; font-size: 0.875rem; }
    .search-hint { padding: 0.625rem 1.25rem; font-size: 0.75rem; color: #475569; border-top: 1px solid #1e293b; display: flex; gap: 0.5rem; }
  `;

  const styleEl = document.createElement('style');
  styleEl.textContent = searchStyle;
  document.head.appendChild(styleEl);
  document.body.insertAdjacentHTML('beforeend', searchHtml);

  const searchModal   = document.getElementById('searchModal');
  const searchInput   = document.getElementById('searchInput');
  const searchResults = document.getElementById('searchResults');

  // Índice de secciones para búsqueda
  const SEARCH_INDEX = [
    { id: 'introduccion', title: 'Introducción', keywords: 'que es sortmatic arquitectura' },
    { id: 'roles',        title: 'Roles de Usuario', keywords: 'administrador supervisor operador permisos' },
    { id: 'login',        title: 'Inicio de Sesión', keywords: 'login acceso contraseña cuenta' },
    { id: 'scada',        title: 'Módulo SCADA – Monitoreo', keywords: 'faja marcha paro arduino control' },
    { id: 'contadores',   title: 'Contadores en Tiempo Real', keywords: 'aprobadas defectuosas nivel bajo contador' },
    { id: 'analiticos',   title: 'Analíticos y KPIs', keywords: 'rendimiento merma cadencia kpi gráfico' },
    { id: 'lotes',        title: 'Gestión de Lotes', keywords: 'lote tamaño capacidad cerrar' },
    { id: 'mermas',       title: 'Galería de Mermas', keywords: 'fotos capturas descartadas galería filtros' },
    { id: 'exportar',     title: 'Exportar Datos', keywords: 'pdf csv descargar reporte' },
    { id: 'parametros',   title: 'Parámetros de Inspección', keywords: 'umbral confianza confidence threshold slider deslizador' },
    { id: 'usuarios',     title: 'Gestión de Usuarios', keywords: 'crear eliminar usuario cuenta' },
    { id: 'auditoria',    title: 'Bitácora de Auditoría', keywords: 'log auditoría registro acciones' },
    { id: 'arquitectura', title: 'Arquitectura Técnica', keywords: 'react django yolo arduino websocket' },
    { id: 'glosario',     title: 'Glosario', keywords: 'términos definiciones bpm scada yolo' },
  ];

  function openSearch() {
    searchModal.style.display = 'flex';
    searchInput.value = '';
    renderSearchResults('');
    setTimeout(() => searchInput.focus(), 50);
  }

  function closeSearch() {
    searchModal.style.display = 'none';
  }

  function renderSearchResults(query) {
    const q = query.toLowerCase().trim();
    const matches = q
      ? SEARCH_INDEX.filter(item =>
          item.title.toLowerCase().includes(q) || item.keywords.includes(q)
        )
      : SEARCH_INDEX;

    if (matches.length === 0) {
      searchResults.innerHTML = '<div class="search-no-results">Sin resultados para "' + query + '"</div>';
      return;
    }

    searchResults.innerHTML = matches.map((item, i) => `
      <div class="search-result-item ${i === 0 ? 'selected' : ''}" data-id="${item.id}">
        <span class="result-icon">→</span>
        ${item.title}
      </div>
    `).join('');

    searchResults.querySelectorAll('.search-result-item').forEach(el => {
      el.addEventListener('click', function () {
        activateSection(this.dataset.id);
        closeSearch();
      });
    });
  }

  searchInput.addEventListener('input', e => renderSearchResults(e.target.value));

  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
      e.preventDefault();
      openSearch();
    }
    if (e.key === 'Escape' && searchModal.style.display !== 'none') {
      closeSearch();
    }
  });

  searchModal.querySelector('.search-backdrop').addEventListener('click', closeSearch);

  /* ============================================================
     INDICADOR DE PROGRESO DE LECTURA
     ============================================================ */
  const progressBar = document.createElement('div');
  progressBar.style.cssText = `
    position: fixed; top: 0; left: 0; height: 2px; width: 0%;
    background: linear-gradient(to right, #06b6d4, #a78bfa);
    z-index: 200; transition: width 0.1s;
  `;
  document.body.appendChild(progressBar);

  window.addEventListener('scroll', function () {
    const scrollTop    = document.documentElement.scrollTop || document.body.scrollTop;
    const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
    const progress     = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;
    progressBar.style.width = progress + '%';
  });

  /* ============================================================
     BOTÓN "BUSCAR" EN LA BARRA LATERAL (tooltip)
     ============================================================ */
  const searchTip = document.createElement('div');
  searchTip.innerHTML = `
    <div style="padding:0.75rem 1rem; border-top:1px solid #1e293b; border-bottom: 1px solid #1e293b;">
      <button onclick="document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true}))"
              style="width:100%;display:flex;align-items:center;gap:0.5rem;background:#1e293b;border:1px solid #334155;
                     border-radius:0.5rem;padding:0.5rem 0.75rem;cursor:pointer;color:#94a3b8;font-size:0.8125rem;
                     font-family:inherit;transition:background 0.15s"
              onmouseover="this.style.background='#334155'" onmouseout="this.style.background='#1e293b'">
        <svg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2'><circle cx='11' cy='11' r='8'/><path d='m21 21-4.35-4.35'/></svg>
        Buscar en el manual
        <span style="margin-left:auto;font-size:0.7rem;background:#0f172a;padding:1px 6px;border-radius:4px;border:1px solid #334155">Ctrl+K</span>
      </button>
    </div>
  `;

  const nav = document.getElementById('nav');
  if (nav) nav.parentNode.insertBefore(searchTip, nav);

  /* ============================================================
     INICIALIZAR
     ============================================================ */
  loadFromHash();

})();
