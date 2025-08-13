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
    const data = await r.json(); // DRF pagination format

    (data.results || []).forEach(item => {
      const node = tpl.content.cloneNode(true);
      const img = node.querySelector('.thumb');
      const path = node.querySelector('.path');
      const size = node.querySelector('.size');
      const copyBtn = node.querySelector('.copy-btn');
      const openBtn = node.querySelector('.open-btn');

      img.src = `/api/datasets/item/${item.id}/image`;
      img.alt = item.image_path;
      path.textContent = item.image_path;
      size.textContent = `${item.width} × ${item.height}`;
      copyBtn.addEventListener('click', () => navigator.clipboard.writeText(item.image_path));
      openBtn.href = img.src;

      grid.appendChild(node);
    });

    // пагинация
    pageInfo.textContent = `Страница ${data.current || qs.get('page') || 1} из ~? (count: ${data.count})`;
    prevBtn.disabled = !data.previous;
    nextBtn.disabled = !data.next;

    prevBtn.onclick = () => {
      const urlPrev = new URL(data.previous, location.origin);
      const page = urlPrev.searchParams.get('page') || '1';
      qs.set('page', page); history.replaceState({}, '', `?${qs.toString()}`);
      load();
    };
    nextBtn.onclick = () => {
      const urlNext = new URL(data.next, location.origin);
      const page = urlNext.searchParams.get('page') || '1';
      qs.set('page', page); history.replaceState({}, '', `?${qs.toString()}`);
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

  // Инициал
  if (!qs.get('page')) { qs.set('page', '1'); history.replaceState({}, '', `?${qs.toString()}`); }
  load();
})();
