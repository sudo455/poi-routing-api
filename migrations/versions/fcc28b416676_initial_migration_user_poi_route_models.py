"""Initial migration - User, POI, Route models

Revision ID: fcc28b416676
Revises:
Create Date: 2026-01-22 15:58:13.076650

"""
from alembic import op
import sqlalchemy as sa
import geoalchemy2

# revision identifiers, used by Alembic.
revision = 'fcc28b416676'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=128), nullable=False),
        sa.Column('rate_limit', sa.Integer(), nullable=True, default=60),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # Create POIs table with PostGIS GEOGRAPHY
    op.create_table('pois',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('location', geoalchemy2.types.Geography(
            geometry_type='POINT',
            srid=4326,
            from_text='ST_GeogFromText',
            name='geography'
        ), nullable=False),
        sa.Column('properties', sa.JSON(), nullable=True),
        sa.Column('osm_id', sa.BigInteger(), nullable=True),
        sa.Column('osm_type', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_pois_name', 'pois', ['name'], unique=False)
    op.create_index('ix_pois_category', 'pois', ['category'], unique=False)
    op.create_index('ix_pois_osm_id', 'pois', ['osm_id'], unique=False)
    # Note: GeoAlchemy2 automatically creates spatial index for Geography columns

    # Create routes table with PostGIS GEOGRAPHY
    op.create_table('routes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('public', sa.Boolean(), nullable=True, default=False),
        sa.Column('vehicle', sa.String(length=20), nullable=True, default='car'),
        sa.Column('owner_id', sa.String(length=36), nullable=True),
        sa.Column('geometry', geoalchemy2.types.Geography(
            geometry_type='LINESTRING',
            srid=4326,
            from_text='ST_GeogFromText',
            name='geography'
        ), nullable=False),
        sa.Column('encoded_polyline', sa.Text(), nullable=True),
        sa.Column('distance_meters', sa.Float(), nullable=True),
        sa.Column('duration_millis', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_routes_owner_id', 'routes', ['owner_id'], unique=False)
    op.create_index('ix_routes_public', 'routes', ['public'], unique=False)
    # Note: GeoAlchemy2 automatically creates spatial index for Geography columns

    # Create route_pois association table
    op.create_table('route_pois',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('route_id', sa.String(length=36), nullable=False),
        sa.Column('poi_id', sa.String(length=36), nullable=True),
        sa.Column('sequence_order', sa.Integer(), nullable=False),
        sa.Column('cached_name', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['poi_id'], ['pois.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['route_id'], ['routes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_route_poi_order', 'route_pois', ['route_id', 'sequence_order'], unique=False)


def downgrade():
    # Drop tables in reverse order of creation
    # Note: spatial indexes are dropped automatically with table drop
    op.drop_index('idx_route_poi_order', table_name='route_pois')
    op.drop_table('route_pois')

    op.drop_index('ix_routes_public', table_name='routes')
    op.drop_index('ix_routes_owner_id', table_name='routes')
    op.drop_table('routes')

    op.drop_index('ix_pois_osm_id', table_name='pois')
    op.drop_index('ix_pois_category', table_name='pois')
    op.drop_index('ix_pois_name', table_name='pois')
    op.drop_table('pois')

    op.drop_index('ix_users_username', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
