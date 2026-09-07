from pydantic import BaseModel


class WorkerStats(BaseModel):
    activos: int
    conTelefono: int
    incorporadosEsteMes: int
    conImei: int


class PhoneStats(BaseModel):
    total: int
    activos: int
    congelados: int
    bajas: int
    sinDatos: int


class RecentDevice(BaseModel):
    id: str
    numero: str | None = None
    grupo: str | None = None
    updated_at: str
    marca: str | None = None
    modelo: str | None = None
    employee_nombre: str | None = None


class MonthlyWorkerStat(BaseModel):
    month: str
    incorporations: int


class DashboardResponse(BaseModel):
    stats: WorkerStats
    phoneStats: PhoneStats
    recentDevices: list[RecentDevice]
    monthlyWorkerStats: list[MonthlyWorkerStat]
