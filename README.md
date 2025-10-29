# IoT Device Monitoring - Edge API (Python)

Edge API para el Bounded Context de **IoT Device Monitoring** usando Domain-Driven Design (DDD) con Python y FastAPI.

## 🌐 Documentación en Línea

- Swagger UI: https://bibflip-edge-api-platform.azurewebsites.net/api/docs

- ReDoc: https://bibflip-edge-api-platform.azurewebsites.net/api/redoc

## 🏗️ Arquitectura DDD

```
iot-edge-api/
├── domain/                      # Domain Layer
│   ├── model/
│   │   └── device.py           # Entidades y Value Objects
│   └── repository/
│       └── device_repository.py # Interfaz del repositorio
│
├── application/                 # Application Layer
│   └── device_service.py       # Casos de uso y lógica de aplicación
│
├── infrastructure/              # Infrastructure Layer
│   └── persistence/
│       └── in_memory_device_repository.py  # Implementación in-memory
│
├── interface/                   # Interface Layer
│   └── api/
│       └── device_controller.py # REST API Controllers
│
├── main.py                      # Entry point
├── requirements.txt             # Dependencias
└── README.md
```

## 📦 Capas DDD

### 1. **Domain Layer** (Núcleo del negocio)
- **Entities**: `Device`
- **Value Objects**: `DeviceId`, `PressureReading`, `Location`
- **Enums**: `DeviceStatus`, `DeviceType`
- **Repository Interface**: `DeviceRepository`

### 2. **Application Layer** (Casos de uso)
- `DeviceService`: Orquesta operaciones del dominio
- Casos de uso:
  - Registrar dispositivo
  - Actualizar lectura de sensor
  - Consultar estado de dispositivos
  - Detectar dispositivos offline

### 3. **Infrastructure Layer** (Implementaciones técnicas)
- `InMemoryDeviceRepository`: Repositorio en memoria (ideal para Edge)
- Puede extenderse con SQLite, PostgreSQL, etc.

### 4. **Interface Layer** (API REST)
- `DeviceController`: Endpoints REST con FastAPI
- DTOs: `RegisterDeviceRequest`, `UpdateReadingRequest`, `DeviceResponse`

## 🚀 Instalación y Ejecución

```bash
# Instalar dependencias
pip install -r requirements.txt

# Ejecutar servidor
python main.py
```

El servidor estará disponible en: `http://localhost:8000`

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc

## 📡 Endpoints Principales

### Registrar Dispositivo
```bash
POST /api/v1/devices
{
  "device_id": "ESP32_001",
  "device_type": "chair_sensor",
  "branch_id": "BRANCH_001",
  "zone": "CAFE_ZONE",
  "position": "TABLE_A1"
}
```

### Actualizar Lectura (desde ESP32)
```bash
POST /api/v1/devices/ESP32_001/readings
{
  "pressure": 75.5,
  "threshold": 30.0
}
```

### Consultar Dispositivos Disponibles
```bash
GET /api/v1/devices/status/available?branch_id=BRANCH_001
```

### Consultar Dispositivos Ocupados
```bash
GET /api/v1/devices/status/occupied
```

### Verificar Dispositivos Offline
```bash
POST /api/v1/devices/maintenance/check-offline?timeout_minutes=5
```

## 🔗 Integración con ESP32

```cpp
// Ejemplo de envío de datos desde ESP32
void enviarLectura(float presion) {
  HTTPClient http;
  http.begin("http://edge-api:8000/api/v1/devices/ESP32_001/readings");
  http.addHeader("Content-Type", "application/json");
  
  String payload = "{\"pressure\":" + String(presion) + ",\"threshold\":30.0}";
  int httpCode = http.POST(payload);
  
  http.end();
}
```

## 🔄 Integración con Backend Spring Boot

Esta Edge API puede sincronizarse con el backend principal:

```python
# Próxima implementación: Event publishing
# - Publicar eventos de cambio de estado
# - Sincronizar con otros Bounded Contexts (Table Management, Booking)
# - Message broker: RabbitMQ, Kafka, etc.
```

## 🔐 Próximas Mejoras

- [ ] Agregar autenticación JWT
- [ ] Implementar Event Sourcing
- [ ] Integrar con Message Broker
- [ ] Agregar persistencia con PostgreSQL
- [ ] WebSocket para updates en tiempo real
- [ ] Métricas y logging avanzado

---

**Bounded Context**: IoT Device Monitoring  
**Lenguaje Ubicuo**: Device, Sensor, Reading, Pressure, Occupied, Available, Branch, Zone


