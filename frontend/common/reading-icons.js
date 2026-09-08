function getEmojiForText(titulo) {
    const tituloNormalizado = (titulo || "")
        .toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "");

    const tematicas = [
        { palabras: ["biblioteca", "bibliotecas"], emoji: "📚" },
        { palabras: ["libro", "libros", "lectura", "leer", "cuento", "cuentos", "fabula", "fabulas"], emoji: "📖" },
        { palabras: ["familia", "familias", "mama", "papa", "hermano", "hogar"], emoji: "👨‍👩‍👧‍👦" },
        { palabras: ["ahorro", "ahorrar", "dinero", "moneda", "finanzas"], emoji: "💰" },
        { palabras: ["perro", "perros", "can", "mascota", "mascotas"], emoji: "🐶" },
        { palabras: ["mochila", "mochilas", "cuaderno", "cuadernos"], emoji: "🎒" },
        { palabras: ["zorro", "zorra"], emoji: "🦊" },
        { palabras: ["leon", "selva", "animal", "animales"], emoji: "🦁" },
        { palabras: ["raton", "ratones"], emoji: "🐭" },
        { palabras: ["escuela", "colegio", "aula", "clase", "profesor", "maestro"], emoji: "🏫" },
        { palabras: ["agua", "rio", "mar", "lluvia", "oceano", "lago"], emoji: "💧" },
        { palabras: ["reciclaje", "reciclar", "residuos", "basura", "contaminacion", "ambiente"], emoji: "♻️" },
        { palabras: ["desayuno", "comida", "alimento", "fruta", "manzana", "uva", "cocina"], emoji: "🍎" },
        { palabras: ["museo", "historia", "arte", "cultura"], emoji: "🏛️" },
        { palabras: ["fotosintesis", "fotosintetica", "hoja", "hojas", "planta", "plantas", "marchita", "semilla"], emoji: "🌿" },
        { palabras: ["parque", "arbol", "bosque", "naturaleza", "sombra", "jardin"], emoji: "🌳" },
        { palabras: ["deporte", "voley", "futbol", "baloncesto", "juego", "competencia", "partido"], emoji: "⚽" },
        { palabras: ["amistad", "amigo", "amigos", "compartir", "ayuda", "solidaridad", "equipo", "equipos", "colaboracion", "trabajo"], emoji: "🤝" },
        { palabras: ["tarea", "estudiar", "aprendizaje", "lapiz", "escribir"], emoji: "✏️" },
        { palabras: ["compras", "comprar", "compra", "mercado", "tienda", "supermercado"], emoji: "🛒" },
        { palabras: ["aventura", "viaje", "explorar", "exploracion"], emoji: "🧭" },
        { palabras: ["espacio", "planeta", "estrella", "universo"], emoji: "🚀" },
        { palabras: ["musica", "cancion", "cantar", "instrumento"], emoji: "🎵" },
        { palabras: ["cumpleanos", "fiesta", "celebracion"], emoji: "🎉" }
    ];

    for (const tematica of tematicas) {
        if (tematica.palabras.some(palabra => tituloNormalizado.includes(palabra))) {
            return tematica.emoji;
        }
    }

    return "📖";
}
