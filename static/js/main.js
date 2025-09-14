document.addEventListener('DOMContentLoaded', () => {
    const token = typeof verificarAutenticacion === 'function' ? verificarAutenticacion() : null;
    if (!token && window.location.pathname !== '/index.html' && window.location.pathname !== '/') {
        return;
    }

    // Initialize functionalities based on the current page
    if (document.getElementById('archived-grid')) {
        initializeArchivedPage(token);
    }

    // The AI modal is on the dashboard, so we initialize it if the trigger button exists
    if (document.getElementById('open-ai-modal-btn')) {
        initializeAIModal(token);
    }
});

function initializeAIModal(token) {
    const openModalBtn = document.getElementById('open-ai-modal-btn');
    const closeModalBtn = document.getElementById('close-ai-modal-btn');
    const modalOverlay = document.getElementById('ai-analyzer-modal');

    if (!openModalBtn || !closeModalBtn || !modalOverlay) {
        console.error('Modal elements not found!');
        return;
    }

    // Function to open the modal
    const openModal = () => {
        modalOverlay.style.display = 'flex';
        setTimeout(() => modalOverlay.classList.add('visible'), 10);
    };

    // Function to close the modal
    const closeModal = () => {
        modalOverlay.classList.remove('visible');
        setTimeout(() => {
            modalOverlay.style.display = 'none';
            clearLyricsAnalysisResults(); // Clear results when closing
        }, 300); // Match CSS transition duration
    };

    // Event listeners
    openModalBtn.addEventListener('click', openModal);
    closeModalBtn.addEventListener('click', closeModal);

    // Close modal if clicking on the overlay background
    modalOverlay.addEventListener('click', (event) => {
        if (event.target === modalOverlay) {
            closeModal();
        }
    });

    // Initialize the lyrics analyzer logic inside the modal
    initializeLyricsAnalyzer(token);
}


async function initializeLyricsAnalyzer(token) {
    const lyricsInput = document.getElementById('lyrics-input');
    const analyzeLyricsBtn = document.getElementById('analyze-lyrics-btn');
    const lyricsAnalysisResults = document.getElementById('lyrics-analysis-results');

    if (!lyricsInput || !analyzeLyricsBtn || !lyricsAnalysisResults) {
        return; // Do not run if elements are not on the page
    }

    analyzeLyricsBtn.addEventListener('click', async () => {
        const lyrics = lyricsInput.value.trim();
        if (!lyrics) {
            alert('Por favor, introduce las letras de la canción para analizar.');
            return;
        }

        analyzeLyricsBtn.disabled = true;
        lyricsAnalysisResults.innerHTML = '<div class="spinner"></div><p>Analizando letras...</p>'; // Improved loading state

        try {
            const response = await fetch('/api/analyze-lyrics', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ lyrics: lyrics })
            });

            const result = await response.json();

            if (result.status === 'success') {
                renderLyricsAnalysisResults(result.words, token);
            } else {
                lyricsAnalysisResults.innerHTML = `<p>Error al analizar letras: ${result.message}</p>`;
            }
        } catch (error) {
            console.error('Error al analizar letras:', error);
            lyricsAnalysisResults.innerHTML = '<p>Error de red al analizar letras.</p>';
        } finally {
            analyzeLyricsBtn.disabled = false;
        }
    });
}

function renderLyricsAnalysisResults(words, token) {
    const resultsContainer = document.getElementById('lyrics-analysis-results');
    resultsContainer.innerHTML = ''; // Clear previous results

    if (words.length === 0) {
        resultsContainer.innerHTML = '<p>No se encontraron palabras nuevas o relevantes.</p>';
        return;
    }

    const ul = document.createElement('ul');
    ul.className = 'lyrics-analysis-list';

    words.forEach(wordData => {
        const li = document.createElement('li');
        li.className = 'lyrics-analysis-item';
        li.id = `word-item-${wordData.word}`;

        let content = `<strong>${wordData.word}</strong> → <strong>${wordData.word_translation}</strong><br>`;
        content += `<small>Ejemplo (EN): <em>${wordData.new_en_phrase}</em></small><br>`;
        content += `<small>Ejemplo (ES): <em>${wordData.new_es_phrase}</em></small><br>`;

        if (wordData.is_duplicate) {
            content += `<span class="duplicate-warning">¡Duplicado! Se actualizarán los ejemplos.</span><br>`;
            
            const replaceBtn = document.createElement('button');
            replaceBtn.textContent = 'Actualizar ejemplos';
            replaceBtn.className = 'btn btn-sm btn-warning';
            replaceBtn.addEventListener('click', () => updateFlashcardPhrases(token, wordData));
            li.innerHTML = content;
            li.appendChild(replaceBtn);

        } else {
            const addBtn = document.createElement('button');
            addBtn.textContent = 'Añadir';
            addBtn.className = 'btn btn-sm btn-success';
            addBtn.addEventListener('click', () => addFlashcard(token, wordData));
            li.innerHTML = content;
            li.appendChild(addBtn);
        }
        ul.appendChild(li);
    });
    resultsContainer.appendChild(ul);
}

async function addFlashcard(token, wordData) {
    try {
        const response = await fetch('/api/flashcards/add', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
                front_content: wordData.word,
                back_content: wordData.word_translation, // Use the single word translation
                category: 'Lyrics',
                example_en: wordData.new_en_phrase, // Use the new example phrase
                example_es: wordData.new_es_phrase
            })
        });
        const result = await response.json();
        if (result.status === 'success') {
            alert('Flashcard añadida con éxito!');
            const listItem = document.getElementById(`word-item-${wordData.word}`);
            if (listItem) {
                listItem.remove();
            }
        } else {
            alert('Error al añadir flashcard: ' + result.message);
        }
    } catch (error) {
        console.error('Error de red al añadir flashcard:', error);
        alert('Error de red al añadir flashcard.');
    }
}

async function updateFlashcardPhrases(token, wordData) {
    try {
        // Note: We are not updating the back_content (the single translation) here,
        // only the example phrases associated with the card.
        const response = await fetch(`/api/flashcards/update_phrases/${wordData.flashcard_id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify({
                // The backend endpoint requires back_content, so we send the existing one.
                // A more advanced implementation could have a dedicated endpoint for just updating examples.
                back_content: wordData.word_translation,
                example_en: wordData.new_en_phrase,
                example_es: wordData.new_es_phrase
            })
        });
        const result = await response.json();
        if (result.status === 'success') {
            alert('Frases de ejemplo actualizadas con éxito!');
            const listItem = document.getElementById(`word-item-${wordData.word}`);
            if (listItem) {
                listItem.remove();
            }
        } else {
            alert('Error al actualizar flashcard: ' + result.message);
        }
    } catch (error) {
        console.error('Error de red al actualizar flashcard:', error);
        alert('Error de red al actualizar flashcard.');
    }
}

function clearLyricsAnalysisResults() {
    const lyricsInput = document.getElementById('lyrics-input');
    const lyricsAnalysisResults = document.getElementById('lyrics-analysis-results');
    if (lyricsInput) {
        lyricsInput.value = '';
    }
    if (lyricsAnalysisResults) {
        lyricsAnalysisResults.innerHTML = '';
    }
}

async function initializeArchivedPage(token) {
    // This function remains unchanged as it belongs to a different page
    const gridContainer = document.getElementById('archived-grid');
    if (!gridContainer) return;
    
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
    const clearSelectionBtn = document.getElementById('clear-selection-btn');

    let cachedTranslation = null;
    let currentPage = 1;
    let currentSearch = '';
    let debounceTimeout;
    const selectedCards = new Map();

    function updateButtonStates() {
        const hasSelection = selectedCards.size > 0;
        if (unarchiveBtn) unarchiveBtn.disabled = !hasSelection;
        if (clearSelectionBtn) clearSelectionBtn.disabled = !hasSelection;
        if (generateBtn) generateBtn.disabled = !hasSelection;
    }

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
                updateButtonStates();
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
            updateButtonStates();
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
                fetchAndRenderArchivedCards(currentPage, currentSearch).then(updateButtonStates);
            } else {
                alert('Error al desarchivar: ' + result.message);
            }
        } catch (error) {
            console.error('Error de red al desarchivar:', error);
            alert('Error de red al desarchivar tarjetas.');
        }
    });

    randomSelectBtn.addEventListener('click', async () => {
        aiSpinner.style.display = 'block';
        randomSelectBtn.disabled = true;
        generateBtn.disabled = true;

        try {
            const response = await fetch('/api/flashcards/archived/random/10', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await response.json();

            if (response.ok && result.status === 'success') {
                selectedCards.clear();
                const randomWords = [];
                result.flashcards.forEach(card => {
                    selectedCards.set(card.id, card.front_content);
                    randomWords.push(card.front_content);
                });

                if (randomWordsList) {
                    randomWordsList.innerHTML = randomWords.map(word => `<li>${word}</li>`).join('');
                }
                if (randomSelectTooltip) {
                    randomSelectTooltip.style.display = 'flex';
                }
                
                await fetchAndRenderArchivedCards(currentPage, currentSearch);
                updateButtonStates();

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
            aiSpinner.style.display = 'none';
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

    if (clearSelectionBtn) {
        clearSelectionBtn.addEventListener('click', () => {
            selectedCards.clear();
            gridContainer.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
                checkbox.checked = false;
            });
            if (randomSelectTooltip) {
                randomSelectTooltip.style.display = 'none';
            }
            gridContainer.querySelectorAll('.archived-card-grid-item.highlight').forEach(cardEl => {
                cardEl.classList.remove('highlight');
            });
            updateButtonStates();
            clearLyricsAnalysisResults();
        });
    }

    await fetchAndRenderArchivedCards();
    updateButtonStates();

    if (translateAccordionBtn) {
        translateAccordionBtn.addEventListener('click', () => {
            const isExpanded = translateAccordionBtn.textContent === '-';

            if (isExpanded) {
                translationWrapper.style.display = 'none';
                translateAccordionBtn.textContent = '+';
            } else {
                if (cachedTranslation) {
                    aiTranslatedParagraph.value = cachedTranslation;
                    translationWrapper.style.display = 'block';
                    translateAccordionBtn.textContent = '-';
                } else {
                    aiTranslatedParagraph.value = 'No se encontró la traducción.';
                    translationWrapper.style.display = 'block';
                }
            }
        });
    }
}
