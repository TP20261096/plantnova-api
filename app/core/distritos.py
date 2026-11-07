
LIMA_CENTRO = (-12.0464, -77.0428)

DISTRITOS: dict[str, tuple[float, float]] = {
    "Ate": (-12.0260, -76.9180),
    "Barranco": (-12.1400, -77.0200),
    "Breña": (-12.0590, -77.0500),
    "Callao": (-12.0500, -77.1200),
    "Carabayllo": (-11.8980, -77.0320),
    "Chorrillos": (-12.1700, -77.0200),
    "Comas": (-11.9400, -77.0600),
    "El Agustino": (-12.0400, -76.9980),
    "Independencia": (-11.9900, -77.0530),
    "Jesús María": (-12.0740, -77.0490),
    "La Molina": (-12.0800, -76.9400),
    "La Victoria": (-12.0670, -77.0170),
    "Lima": LIMA_CENTRO,
    "Lince": (-12.0870, -77.0360),
    "Los Olivos": (-11.9700, -77.0700),
    "Lurín": (-12.2750, -76.8800),
    "Magdalena del Mar": (-12.0920, -77.0720),
    "Miraflores": (-12.1200, -77.0300),
    "Pachacámac": (-12.2300, -76.8600),
    "Pueblo Libre": (-12.0740, -77.0630),
    "Puente Piedra": (-11.8650, -77.0760),
    "Rímac": (-12.0280, -77.0290),
    "San Borja": (-12.1000, -76.9980),
    "San Isidro": (-12.0970, -77.0360),
    "San Juan de Lurigancho": (-11.9800, -76.9970),
    "San Juan de Miraflores": (-12.1600, -76.9700),
    "San Luis": (-12.0760, -76.9980),
    "San Martín de Porres": (-12.0100, -77.0800),
    "San Miguel": (-12.0770, -77.0900),
    "Santa Anita": (-12.0450, -76.9700),
    "Santiago de Surco": (-12.1350, -76.9900),
    "Surquillo": (-12.1120, -77.0150),
    "Villa El Salvador": (-12.2130, -76.9380),
    "Villa María del Triunfo": (-12.1600, -76.9400),
}


def coordenadas(distrito: str | None) -> tuple[float, float]:
    return DISTRITOS.get(distrito or "", LIMA_CENTRO)