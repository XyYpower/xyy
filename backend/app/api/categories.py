import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.note import CategoryCreate, CategoryOut, CategoryUpdate
from app.services import note_service
from app.utils.deps import get_current_user
from app.utils.response import success

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    categories = await note_service.get_categories_for_user(db, current_user.id)
    return success([CategoryOut.model_validate(c) for c in categories])


@router.post("")
async def create_category(
    data: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    category = await note_service.create_category(db, current_user.id, data)
    return success(CategoryOut.model_validate(category))


@router.put("/{category_id}")
async def update_category(
    category_id: uuid.UUID,
    data: CategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    category = await note_service.update_category(db, current_user.id, category_id, data)
    return success(CategoryOut.model_validate(category))


@router.delete("/{category_id}")
async def delete_category(
    category_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await note_service.delete_category(db, current_user.id, category_id)
    return success(message="Deleted")


BAJGU_PRESETS = [
    {"name": "Java 基础", "description": "集合、泛型、异常、IO、NIO", "sort_order": 1},
    {"name": "JVM", "description": "内存模型、GC、类加载、调优", "sort_order": 2},
    {"name": "并发编程", "description": "线程池、锁、CAS、AQS、volatile", "sort_order": 3},
    {"name": "Spring", "description": "IoC、AOP、事务、Boot、Security", "sort_order": 4},
    {"name": "Redis", "description": "数据结构、持久化、集群、缓存问题", "sort_order": 5},
    {"name": "MySQL", "description": "索引、事务、锁、优化、分库分表", "sort_order": 6},
    {"name": "计算机网络", "description": "TCP/UDP、HTTP/HTTPS、DNS", "sort_order": 7},
    {"name": "操作系统", "description": "进程/线程、内存管理、IO 模型", "sort_order": 8},
    {"name": "系统设计", "description": "分布式、微服务、消息队列、限流", "sort_order": 9},
    {"name": "算法", "description": "数据结构、排序、动态规划、图", "sort_order": 10},
]


@router.post("/presets")
async def create_preset_categories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """一键创建八股文分类预设。"""
    created = []
    for preset in BAJGU_PRESETS:
        data = CategoryCreate(name=preset["name"], description=preset["description"], sort_order=preset["sort_order"])
        category = await note_service.create_category(db, current_user.id, data)
        created.append(CategoryOut.model_validate(category))
    return success(created)
