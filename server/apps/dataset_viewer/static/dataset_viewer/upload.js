(function () {
  const dsId = window.__FLUXLAB__.datasetId;
  const drop = document.getElementById('u-drop');
  const choose = document.getElementById('u-choose');
  const input = document.getElementById('u-input');
  const queueEl = document.getElementById('u-queue');

  if (!drop || !choose || !input || !queueEl) return;

  const MAX_PARALLEL = 3;
  const accept = ['image/jpeg','image/png','image/webp'];

  function getCookie(name) {
    const m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
    return m ? m.pop() : '';
  }
  const csrftoken = getCookie('csrftoken');

  const state = {
    pending: [],
    active: 0,
  };

  choose.addEventListener('click', () => input.click());
  input.addEventListener('change', () => {
    if (input.files && input.files.length) enqueueFiles(Array.from(input.files));
    input.value = '';
  });

  ;['dragenter','dragover'].forEach(ev => {
    drop.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); drop.classList.add('dragover'); });
  });
  ;['dragleave','dragend','drop'].forEach(ev => {
    drop.addEventListener(ev, e => { e.preventDefault(); e.stopPropagation(); drop.classList.remove('dragover'); });
  });
  drop.addEventListener('drop', e => {
    const files = Array.from(e.dataTransfer.files || []);
    enqueueFiles(files);
  });

  function enqueueFiles(files) {
    const filtered = files.filter(f => accept.includes(f.type || ''));
    filtered.forEach(file => {
      const item = makeItem(file);
      state.pending.push(item);
      queueEl.appendChild(item.el);
    });
    pump();
  }

  function makeItem(file) {
    const el = document.createElement('div');
    el.className = 'u-item';
    el.innerHTML = `
      <div>
        <div class="u-name"></div>
        <div class="u-bar"><div></div></div>
        <div class="u-status">В очереди…</div>
      </div>
      <div class="u-actions">
        <button class="u-cancel">Отменить</button>
        <button class="u-retry" style="display:none">Повторить</button>
      </div>
    `;
    el.querySelector('.u-name').textContent = `${file.name} (${Math.round(file.size/1024)} KB)`;
    const bar = el.querySelector('.u-bar > div');
    const status = el.querySelector('.u-status');
    const btnCancel = el.querySelector('.u-cancel');
    const btnRetry = el.querySelector('.u-retry');

    let xhr = null;
    let canceled = false;

    function upload() {
      status.textContent = 'Подготовка…';
      el.classList.remove('success','error');
      btnRetry.style.display = 'none';
      btnCancel.style.display = '';

      const form = new FormData();
      form.append('files', file); // сервер должен принимать files[]

      xhr = new XMLHttpRequest();
      xhr.open('POST', `/api/datasets/${dsId}/upload`);
      xhr.setRequestHeader('X-CSRFToken', csrftoken || '');
      xhr.upload.onprogress = (e) => {
        if (!e.lengthComputable) return;
        const pct = Math.round((e.loaded / e.total) * 100);
        bar.style.width = pct + '%';
        status.textContent = `Загрузка… ${pct}%`;
      };
      xhr.onreadystatechange = () => {
        if (xhr.readyState !== 4) return;
        if (xhr.status >= 200 && xhr.status < 300) {
          bar.style.width = '100%';
          status.textContent = 'Готово';
          el.classList.add('success');
          btnCancel.style.display = 'none';
          // сообщим grid перезагрузиться
          if (typeof window.__reloadGrid === 'function') window.__reloadGrid();
        } else {
          status.textContent = `Ошибка: ${xhr.status}`;
          el.classList.add('error');
          btnRetry.style.display = '';
        }
        state.active--;
        pump();
      };
      xhr.onerror = () => {
        status.textContent = 'Ошибка сети';
        el.classList.add('error');
        btnRetry.style.display = '';
        state.active--;
        pump();
      };
      xhr.send(form);
    }

    btnCancel.addEventListener('click', () => {
      canceled = true;
      try { xhr && xhr.abort(); } catch {}
      status.textContent = 'Отменено';
      el.classList.add('error');
      btnCancel.style.display = 'none';
      // Если был в активе — освободим слот
      if (state.active > 0) { state.active--; pump(); }
    });

    btnRetry.addEventListener('click', () => {
      canceled = false;
      bar.style.width = '0%';
      status.textContent = 'Повтор…';
      el.classList.remove('error');
      state.pending.push({ el, file, upload, canceled });
      pump();
    });

    return { el, file, upload, get canceled(){return canceled;} };
  }

  function pump() {
    while (state.active < MAX_PARALLEL && state.pending.length) {
      const next = state.pending.shift();
      if (next.canceled) continue;
      state.active++;
      next.upload();
    }
  }
})();
