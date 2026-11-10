from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.project_image_layer import ProjectImageLayer
from app.schemas.project import ImageLayer


def sync_project_image_layers(db: Session, project_id: str, layers: list[ImageLayer]) -> None:
    """Keep queryable image-layer rows in the same transaction as the project document."""
    current = list(db.scalars(select(ProjectImageLayer).where(ProjectImageLayer.project_id == project_id)))
    by_layer_id = {row.layer_id: row for row in current}
    incoming_ids = {layer.id for layer in layers}
    stale_ids = set(by_layer_id) - incoming_ids
    if stale_ids:
        db.execute(delete(ProjectImageLayer).where(
            ProjectImageLayer.project_id == project_id,
            ProjectImageLayer.layer_id.in_(stale_ids),
        ))

    for position, layer in enumerate(layers):
        row = by_layer_id.get(layer.id)
        values = {
            "project_id": project_id,
            "layer_id": layer.id,
            "asset_id": layer.assetId,
            "position": position,
            "name": layer.name,
            "visible": layer.visible,
            "locked": layer.locked,
            "opacity": layer.opacity,
            "blend_mode": layer.blendMode,
            "x": layer.x,
            "y": layer.y,
            "scale": layer.scale,
            "rotation": layer.rotation,
            "crop_left": layer.cropLeft,
            "crop_top": layer.cropTop,
            "crop_right": layer.cropRight,
            "crop_bottom": layer.cropBottom,
        }
        if row is None:
            db.add(ProjectImageLayer(**values))
        else:
            for field, value in values.items():
                setattr(row, field, value)


def image_layer_response(row: ProjectImageLayer) -> dict[str, object]:
    return {
        "id": row.layer_id,
        "assetId": row.asset_id,
        "name": row.name,
        "visible": row.visible,
        "locked": row.locked,
        "opacity": row.opacity,
        "blendMode": row.blend_mode,
        "x": row.x,
        "y": row.y,
        "scale": row.scale,
        "rotation": row.rotation,
        "cropLeft": row.crop_left,
        "cropTop": row.crop_top,
        "cropRight": row.crop_right,
        "cropBottom": row.crop_bottom,
    }


def project_response(project, layer_rows: list[ProjectImageLayer]) -> dict[str, object]:
    document = dict(project.document)
    if layer_rows:
        document["imageLayers"] = [image_layer_response(row) for row in layer_rows]
    return {
        "id": project.id,
        "name": project.name,
        "document": document,
        "created_at": project.created_at,
        "updated_at": project.updated_at,
        "revision": project.revision,
    }
