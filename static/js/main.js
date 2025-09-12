document.addEventListener('DOMContentLoaded', () => {
    const token = typeof verificarAutenticacion === 'function' ? verificarAutenticacion() : null;
    if (!token && window.location.pathname !== '/index.html' && window.location.pathname !== '/') {
        return;
    }

    if (document.getElementById('archived-grid')) {
        initializeArchivedPage(token);
    }
});

function initializeArchivedPage(token) {
    // --- Elementos del DOM ---
    const gridContainer = document.getElementById('archived-grid');
    const paginationControls = document.getElementById('pagination-controls');
    const searchInput = document.getElementById('search-input');
    const unarchiveForm = document.getElementById('unarchive-form');
    const unarchiveBtn = document.getElementById('unarchive-btn');
    const generateBtn = document.getElementById('generate-paragraph-btn');
    const aiResultContainer = document.getElementById('ai-result-container');
    const aiParagraph = document.getElementById('ai-generated-paragraph');
    const aiSpinner = document.getElementById('ai-loading-spinner');
    
    const aiTranslatedParagraph = document.getElementById('ai-translated-paragraph');
    const randomSelectBtn = document.getElementById('random-select-btn');
    const randomSelectTooltip = document.getElementById('random-select-tooltip-container');
    const randomWordsList = document.getElementById('random-words-list');
    const translateAccordionBtn = document.getElementById('translate-accordion-btn');
    const translationWrapper = document.getElementById('translation-wrapper');

    // --- Estado de la Aplicación ---
    let cachedTranslation = null;
    let currentPage = 1;
    let currentSearch = '';
    let debounceTimeout;
    const selectedCards = new Map();

    // --- Funciones Principales ---

    function debounce(func, delay) {
        return function(...args) {
            clearTimeout(debounceTimeout);
            debounceTimeout = setTimeout(() => {
                func.apply(this, args);
            }, delay);
        };
    }

    async function fetchAndRenderArchivedCards(page = 1, search = '') {
        try {
            const url = `/api/flashcards/archived?page=${page}&search=${encodeURIComponent(search)}`;
            const response = await fetch(url, { headers: { 'Authorization': `Bearer ${token}` } });
            if (!response.ok) throw new Error('Error en la respuesta del servidor.');
            
            const data = await response.json();
            if (data.status === 'success') {
                renderGrid(data.flashcards);
                renderPagination(data);
                currentPage = data.page;
                currentSearch = search;
            } else {
                gridContainer.innerHTML = `<p>Error al cargar tarjetas: ${data.message}</p>`;
            }
        } catch (err) {
            console.error("Fetch error:", err);
            gridContainer.innerHTML = `<p>Error de red al cargar tarjetas archivadas.</p>`;
        }
    }

    function renderGrid(cards) {
        gridContainer.innerHTML = '';
        if (cards.length === 0) {
            gridContainer.innerHTML = '<p>No se encontraron tarjetas con los criterios actuales.</p>';
            if(unarchiveBtn) unarchiveBtn.style.display = 'none';
            if(generateBtn) generateBtn.style.display = 'none';
            return;
        }

        if(unarchiveBtn) unarchiveBtn.style.display = 'block';
        if(generateBtn) generateBtn.style.display = 'block';
        
        cards.forEach(card => {
            const cardDiv = document.createElement('div');
            cardDiv.className = 'archived-card-grid-item';
            const isChecked = selectedCards.has(card.id);
            cardDiv.innerHTML = `
                <div class="card-content" data-word="${card.front_content}">${card.front_content}</div>
                <div class="card-category">(${card.category})</div>
                <input type="checkbox" name="card_id" value="${card.id}" id="card-${card.id}" ${isChecked ? 'checked' : ''}>
            `;
            gridContainer.appendChild(cardDiv);
        });
    }

    function renderPagination(data) {
        paginationControls.innerHTML = '';
        if (data.total_pages <= 1) return;

        const { page, total_pages } = data;
        let paginationHtml = '';

        paginationHtml += `<button type="button" class="pagination-btn" data-page="1" ${page === 1 ? 'disabled' : ''}>&laquo; Primera</button>`;
        paginationHtml += `<button type="button" class="pagination-btn" data-page="${page - 1}" ${page === 1 ? 'disabled' : ''}>&larr; Anterior</button>`;

        const pagesToShow = 5;
        let startPage = Math.max(1, page - Math.floor(pagesToShow / 2));
        let endPage = Math.min(total_pages, startPage + pagesToShow - 1);

        if (endPage - startPage + 1 < pagesToShow) {
            startPage = Math.max(1, endPage - pagesToShow + 1);
        }

        if (startPage > 1) {
            paginationHtml += `<button type="button" class="pagination-btn" data-page="1">1</button>`;
            if (startPage > 2) {
                paginationHtml += `<span class="pagination-ellipsis">...</span>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationHtml += `<button type="button" class="pagination-btn ${i === page ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }

        if (endPage < total_pages) {
            if (endPage < total_pages - 1) {
                paginationHtml += `<span class="pagination-ellipsis">...</span>`;
            }
            paginationHtml += `<button type="button" class="pagination-btn" data-page="${total_pages}">${total_pages}</button>`;
        }

        paginationHtml += `<button type="button" class="pagination-btn" data-page="${page + 1}" ${page === total_pages ? 'disabled' : ''}>Siguiente &rarr;</button>`;
        paginationHtml += `<button type="button" class="pagination-btn" data-page="${total_pages}" ${page === total_pages ? 'disabled' : ''}>Última &raquo;</button>`;

        paginationControls.innerHTML = paginationHtml;
    }

    

    // --- Event Listeners Generales ---

    const debouncedSearch = debounce((searchTerm) => fetchAndRenderArchivedCards(1, searchTerm), 300);
    searchInput.addEventListener('input', (event) => debouncedSearch(event.target.value));

    paginationControls.addEventListener('click', (event) => {
        const target = event.target.closest('.pagination-btn');
        if (!target || target.disabled) return;
        const page = parseInt(target.dataset.page);
        if (page) fetchAndRenderArchivedCards(page, currentSearch);
    });

    gridContainer.addEventListener('change', (event) => {
        if (event.target.name === 'card_id') {
            // On manual selection, clear highlights and hide tooltip
            gridContainer.querySelectorAll('.archived-card-grid-item.highlight').forEach(cardEl => {
                cardEl.classList.remove('highlight');
            });
            if (randomSelectTooltip) {
                randomSelectTooltip.style.display = 'none';
            }

            const checkbox = event.target;
            const cardId = parseInt(checkbox.value);
            const cardWord = checkbox.closest('.archived-card-grid-item').querySelector('.card-content').dataset.word;
            if (checkbox.checked) {
                selectedCards.set(cardId, cardWord);
            } else {
                selectedCards.delete(cardId);
            }
        }
    });

    unarchiveForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const cardIdsToUnarchive = Array.from(selectedCards.keys());
        if (cardIdsToUnarchive.length === 0) {
            alert('Por favor, selecciona al menos una tarjeta para desarchivar.');
            return;
        }
        try {
            const response = await fetch('/api/flashcards/unarchive', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ card_ids: cardIdsToUnarchive })
            });
            const result = await response.json();
            if (result.status === 'success') {
                alert(result.message);
                selectedCards.clear();
                fetchAndRenderArchivedCards(currentPage, currentSearch);
            } else {
                alert('Error al desarchivar: ' + result.message);
            }
        } catch (error) {
            console.error('Error de red al desarchivar:', error);
            alert('Error de red al desarchivar tarjetas.');
        }
    });

    randomSelectBtn.addEventListener('click', async () => {
        aiSpinner.style.display = 'block'; // Show spinner
        randomSelectBtn.disabled = true;
        generateBtn.disabled = true;

        try {
            const response = await fetch('/api/flashcards/archived/random/10', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                selectedCards.clear(); // Clear previous selections
                const randomWords = [];
                result.flashcards.forEach(card => {
                    selectedCards.set(card.id, card.front_content);
                    randomWords.push(card.front_content);
                });

                // Populate and show tooltip
                if (randomWordsList) {
                    randomWordsList.innerHTML = randomWords.map(word => `<li>${word}</li>`).join('');
                }
                if (randomSelectTooltip) {
                    randomSelectTooltip.style.display = 'flex';
                }
                
                // Refresh the current view to show the new selections
                await fetchAndRenderArchivedCards(currentPage, currentSearch);

                // Highlight newly selected cards visible on the current page
                gridContainer.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
                    const cardItem = checkbox.closest('.archived-card-grid-item');
                    if (cardItem) {
                        cardItem.classList.add('highlight');
                    }
                });

            } else {
                alert(`Error al seleccionar tarjetas aleatorias: ${result.message}`);
            }
        } catch (error) {
            console.error('Error en la selección aleatoria:', error);
            alert('Error de red al intentar seleccionar tarjetas aleatorias.');
        } finally {
            aiSpinner.style.display = 'none'; // Hide spinner
            randomSelectBtn.disabled = false;
            generateBtn.disabled = false;
        }
    });

    generateBtn.addEventListener('click', async () => {
        const words = Array.from(selectedCards.values());
        if (words.length === 0) {
            alert('Por favor, selecciona al menos una palabra para generar el párrafo.');
            return;
        }

        aiResultContainer.style.display = 'block';
        aiSpinner.style.display = 'block';
        aiParagraph.value = 'Generando párrafo...';
        generateBtn.disabled = true;
        
        translationWrapper.style.display = 'none';
        aiTranslatedParagraph.value = '';
        translateAccordionBtn.style.display = 'none';

        try {
            const response = await fetch('/api/generate-paragraph', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ words: words })
            });
            const result = await response.json();
            if (response.ok && result.status === 'success') {
                aiParagraph.value = result.english_paragraph;
                cachedTranslation = result.spanish_paragraph;
                
                if (translateAccordionBtn) {
                    translateAccordionBtn.textContent = '+';
                    translateAccordionBtn.style.display = 'block';
                }
            } else {
                aiParagraph.value = `Error: ${result.message || 'No se pudo obtener el párrafo.'}`;
            }
        } catch (error) {
            console.error('Error al generar párrafo:', error);
            aiParagraph.value = 'Error de conexión con el servidor al generar el párrafo.';
        } finally {
            aiSpinner.style.display = 'none';
            generateBtn.disabled = false;
        }
    });

    // --- Inicialización ---
    fetchAndRenderArchivedCards();

    if (translateAccordionBtn) {
        translateAccordionBtn.addEventListener('click', () => {
            const isExpanded = translateAccordionBtn.textContent === '-';

            if (isExpanded) {
                translationWrapper.style.display = 'none';
                translateAccordionBtn.textContent = '+';
            } else {
                // Expand
                if (cachedTranslation) {
                    aiTranslatedParagraph.value = cachedTranslation;
                    translationWrapper.style.display = 'block';
                    translateAccordionBtn.textContent = '-';
                } else {
                    // This case should not happen if backend works correctly
                    aiTranslatedParagraph.value = 'No se encontró la traducción.';
                    translationWrapper.style.display = 'block';
                }
            }
        });
    }
}