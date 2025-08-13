let currentDataset = null;
let nextUrl = null;
const grid = document.getElementById('grid');
const datasetSelect = document.getElementById('dataset-select');
const itemsCount = document.getElementById('items-count');
const loadMoreBtn = document.getElementById('load-more');

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type} show`;
    setTimeout(() => {
        toast.className = 'toast';
    }, 3000);
}

async function loadDatasets() {
    try {
        const resp = await fetch('/api/datasets/');
        if (!resp.ok) throw new Error('Не удалось получить список датасетов');
        const data = await resp.json();
        datasetSelect.innerHTML = '<option value="">Выберите датасет</option>';
        data.forEach(ds => {
            const opt = document.createElement('option');
            opt.value = ds.id;
            opt.textContent = ds.name;
            opt.dataset.name = ds.name;
            opt.dataset.count = ds.items_count;
            datasetSelect.appendChild(opt);
        });
    } catch (e) {
        showToast(e.message, 'error');
    }
}

async function selectDataset(id) {
    currentDataset = id;
    grid.innerHTML = '';
    nextUrl = `/api/datasets/${id}/items/`;
    itemsCount.textContent = datasetSelect.options[datasetSelect.selectedIndex].dataset.count;
    await loadPage();
}

async function loadPage(url) {
    const target = url || nextUrl;
    if (!target) return;
    try {
        const resp = await fetch(target);
        if (!resp.ok) throw new Error('Ошибка загрузки элементов');
        const data = await resp.json();
        data.results.forEach(item => renderItem(item));
        nextUrl = data.next;
        toggleLoadMore();
    } catch (e) {
        showToast(e.message, 'error');
    }
}

function renderItem(item) {
    const card = document.createElement('div');
    card.className = 'card';

    const img = document.createElement('img');
    img.className = 'thumb skeleton';
    img.src = `/api/datasets/items/${item.id}/thumbnail/`;
    img.onload = () => img.classList.remove('skeleton');
    img.onclick = () => openModal(item);
    card.appendChild(img);

    const caption = document.createElement('div');
    caption.className = 'caption';
    caption.textContent = `${item.width}x${item.height} ${item.sha256}`;
    card.appendChild(caption);

    grid.appendChild(card);
}

function toggleLoadMore() {
    if (nextUrl) {
        loadMoreBtn.style.display = 'block';
    } else {
        loadMoreBtn.style.display = 'none';
    }
}

function setupObserver() {
    const sentinel = document.getElementById('sentinel');
    const observer = new IntersectionObserver(entries => {
        if (entries[0].isIntersecting) {
            loadPage();
        }
    });
    observer.observe(sentinel);
}

function openModal(item) {
    const modal = document.getElementById('modal');
    const img = document.getElementById('modal-image');
    const link = document.getElementById('modal-download');
    const url = `/api/datasets/items/${item.id}/file`;
    img.src = url;
    link.href = url;
    modal.classList.remove('hidden');
}

function closeModal() {
    const modal = document.getElementById('modal');
    modal.classList.add('hidden');
    document.getElementById('modal-image').src = '';
}

document.getElementById('modal-close').onclick = closeModal;
document.getElementById('modal').onclick = e => {
    if (e.target.id === 'modal') closeModal();
};

loadMoreBtn.onclick = () => loadPage();

datasetSelect.onchange = () => {
    if (datasetSelect.value) {
        selectDataset(datasetSelect.value);
    } else {
        grid.innerHTML = '';
        itemsCount.textContent = '';
    }
};

document.getElementById('rescan-btn').onclick = async () => {
    if (!datasetSelect.value) return;
    const name = datasetSelect.options[datasetSelect.selectedIndex].dataset.name;
    const rootDir = document.getElementById('root-dir').value;
    try {
        const resp = await fetch('/api/datasets/scan', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({name: name, root_dir: rootDir})
        });
        if (!resp.ok) {
            const text = await resp.text();
            throw new Error(text || 'Ошибка пересканирования');
        }
        showToast('Пересканировано успешно', 'success');
        await loadDatasets();
        datasetSelect.value = currentDataset;
        selectDataset(currentDataset);
    } catch (e) {
        showToast(e.message, 'error');
    }
};

loadDatasets();
setupObserver();
