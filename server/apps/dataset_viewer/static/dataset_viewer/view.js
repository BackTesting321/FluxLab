(async function () {
  const dsId = window.__FLUXLAB__.datasetId;
  const qs = new URLSearchParams(location.search);
  const grid = document.getElementById('grid');
  const pager = document.getElementById('pager');
  const prevBtn = document.getElementById('prev-btn');
  const nextBtn = document.getElementById('next-btn');
  const pageInfo = document.getElementById('page-info');
  const tpl = document.getElementById('card-tpl');
  const meta = document.getElementById('ds-meta');
  const form = document.getElementById('filters-form');
  const resetBtn = document.getElementById('reset-btn');

    // Modal elements
  const modal = document.getElementById('itemModal');
  const modalImg = document.getElementById('modalImage');
  const metaId = document.getElementById('metaId');
  const metaSize = document.getElementById('metaSize');
  const metaPath = document.getElementById('metaPath');
  const metaSha = document.getElementById('metaSha');
  const deleteBtn = document.getElementById('deleteItemBtn');
  const navPrev = document.getElementById('navPrev');
  const navNext = document.getElementById('navNext');

  let items = [];
  let currentIndex = 0;
  let modalOpen = false;

  function closeModal() {
    modal.hidden = true;
    document.body.style.overflow = '';
    modalOpen = false;
  }

  async function openModalByIndex(idx) {
    if (idx < 0 || idx >= items.length) return;
    currentIndex = idx;
    const item = items[idx];
    modal.hidden = false;
    document.body.style.overflow = 'hidden';
    modalOpen = true;

    modalImg.src = '';
    metaId.textContent = metaSize.textContent = metaPath.textContent = metaSha.textContent = '';
    try {
      const r = await fetch(`/api/datasets/${dsId}/items/${item.id}/`);
      const data = await r.json();
      modalImg.src = data.image_url || item.image_url;
      metaId.textContent = data.id;
      metaSize.textContent = `${data.width} × ${data.height}`;
      metaPath.textContent = data.image_path;
      metaSha.textContent = data.sha256;
    } catch (e) { /* ignore */ }

    navPrev.disabled = idx <= 0;
    navNext.disabled = idx >= items.length - 1;
    const closeBtn = modal.querySelector('.flx-modal__close');
    closeBtn && closeBtn.focus();
  }

  function openModalById(id) {
    const idx = items.findIndex(it => it.id === id);
    if (idx !== -1) openModalByIndex(idx);
  }

  // Подтянем мету датасета
  try {
    const r = await fetch(`/api/datasets/${dsId}/`);
    const data = await r.json();
    meta.textContent = `Путь: ${data.root_dir} · элементов: ${data.items_count}`;
  } catch (e) {
    meta.textContent = 'Не удалось загрузить сведения о датасете';
  }

  function paramsFromForm() {
    const fd = new FormData(form);
    const p = new URLSearchParams();
    for (const [k, v] of fd.entries()) {
      if (v !== '') p.set(k, v);
    }
    // страница
    p.set('page', qs.get('page') || '1');
    return p;
  }

  async function load() {
    grid.innerHTML = '';
    pageInfo.textContent = 'Загрузка…';
    prevBtn.disabled = true; nextBtn.disabled = true;

    const p = paramsFromForm();
    const url = `/api/datasets/${dsId}/items?` + p.toString();
    const r = await fetch(url);
    const data = await r.json();

    items = data.results || [];
    items.forEach(item => {
      const node = tpl.content.cloneNode(true);
      const img = node.querySelector('.thumb');
      const path = node.querySelector('.path');
      const size = node.querySelector('.size');
      const copyBtn = node.querySelector('.copy-btn');
      const openBtn = node.querySelector('.open-btn');
      const card = node.querySelector('.card');

      img.src = item.thumb_url || item.image_url;
      img.alt = item.image_path;
      img.onerror = () => { img.onerror = null; img.src = item.image_url; };
      path.textContent = item.image_path;
      size.textContent = `${item.width} × ${item.height}`;
      copyBtn.addEventListener('click', (e) => { e.stopPropagation(); navigator.clipboard.writeText(item.image_path); });
      openBtn.href = item.image_url;
      openBtn.addEventListener('click', e => e.stopPropagation());
      card.dataset.id = item.id;
      card.querySelector('.thumb-wrap').addEventListener('click', () => openModalById(item.id));

      grid.appendChild(node);
    });

    // пагинация
       const page = data.page || parseInt(qs.get('page') || '1');
    const pageSize = data.page_size || parseInt(qs.get('page_size') || '50');
    const total = data.count || 0;
    pageInfo.textContent = `Страница ${page} · размер ${pageSize} · всего ${total}`;
    const hasPrev = page > 1;
    const hasNext = page * pageSize < total;
    prevBtn.disabled = !hasPrev;
    nextBtn.disabled = !hasNext;

    prevBtn.onclick = () => {
      qs.set('page', String(page - 1));
      history.replaceState({}, '', `?${qs.toString()}`);
      load();
    };
    nextBtn.onclick = () => {
      qs.set('page', String(page + 1));
      history.replaceState({}, '', `?${qs.toString()}`);
      load();
    };
  }

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    qs.set('page', '1');
    history.replaceState({}, '', `?${qs.toString()}`);
    load();
  });

  resetBtn.addEventListener('click', () => {
    form.reset();
    qs.set('page', '1');
    history.replaceState({}, '', `?${qs.toString()}`);
    load();
  });

  // Modal events
  navPrev.addEventListener('click', () => openModalByIndex(currentIndex - 1));
  navNext.addEventListener('click', () => openModalByIndex(currentIndex + 1));
  modal.addEventListener('click', (e) => {
    if (e.target.dataset.close !== undefined) closeModal();
  });
  document.addEventListener('keydown', (e) => {
    if (!modalOpen) return;
    if (e.key === 'Escape') closeModal();
    if (e.key === 'ArrowLeft') openModalByIndex(currentIndex - 1);
    if (e.key === 'ArrowRight') openModalByIndex(currentIndex + 1);
  });
  deleteBtn.addEventListener('click', async () => {
    if (!confirm('Удалить этот элемент?')) return;
    const item = items[currentIndex];
    const r = await fetch(`/api/datasets/${dsId}/items/${item.id}/`, { method: 'DELETE' });
    if (r.ok) {
      const card = grid.querySelector(`.card[data-id="${item.id}"]`);
      card && card.remove();
      const m = meta.textContent.match(/элементов: (\d+)/);
      if (m) {
        const newCount = Math.max(0, parseInt(m[1]) - 1);
        meta.textContent = meta.textContent.replace(/элементов: \d+/, `элементов: ${newCount}`);
      }
      items.splice(currentIndex, 1);
      closeModal();
      if (items.length === 0) {
        load();
      } else if (currentIndex >= items.length) {
        currentIndex = items.length - 1;
      }
    }
  });

  // Инициал
  if (!qs.get('page')) { qs.set('page', '1'); history.replaceState({}, '', `?${qs.toString()}`); }
  load();

    // дать доступ uploader-скрипту обновить сетку
  window.__reloadGrid = () => {
    // сбросим на первую страницу — по желанию:
    // const qs = new URLSearchParams(location.search);
    // qs.set('page','1'); history.replaceState({}, '', `?${qs.toString()}`);
    // затем просто перегрузим текущую страницу данных
    (typeof load === 'function') && load();
  };
})();