-- 1. Elimina la vecchia tabella
DROP TABLE IF EXISTS arredamento;

-- 2. Crea la nuova tabella con acquista_sn default 'N'
CREATE TABLE arredamento (
    id SERIAL PRIMARY KEY,
    articolo TEXT,
    acquistato NUMERIC DEFAULT 1,
    costo NUMERIC DEFAULT 0,
    importo_totale NUMERIC DEFAULT 0,
    acquista_sn TEXT DEFAULT 'N', -- Default impostato a 'N'
    note TEXT,
    prezzo_pieno NUMERIC DEFAULT 0,
    sconto_perc NUMERIC DEFAULT 0,
    stato_pagamento TEXT,
    versato NUMERIC DEFAULT 0,
    link_fattura TEXT,
    data_scadenza DATE,
    stanza_chiusa BOOLEAN DEFAULT FALSE,
    link TEXT,
    foto TEXT,
    stanza TEXT, -- Qui andrà 'Camera', 'Cucina'... o 'Wishlist'
    created_at TIMESTAMPTZ DEFAULT NOW()
);
