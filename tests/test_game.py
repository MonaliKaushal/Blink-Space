import pytest
from game import _is_solid, Enemy

def test_is_solid():
    # Top-left corner is typically a wall (1)
    assert _is_solid(0, 0) == True
    # Inside the map (e.g., 9, 9) is usually open (0)
    assert _is_solid(9, 9) == False
    # Out of bounds should be treated as solid
    assert _is_solid(-1, -1) == True
    assert _is_solid(100, 100) == True

def test_enemy_take_hit():
    # Create an enemy with 3 HP at position (0,0)
    mock_sprites = {"walk1": None, "walk2": None, "hurt": None}
    enemy = Enemy(x=0.0, y=0.0, hp=3, speed=1.0, sprites=mock_sprites)
    
    assert enemy.hp == 3
    assert enemy.alive == True
    
    # Take first hit
    killed = enemy.take_hit()
    assert killed == False
    assert enemy.hp == 2
    
    # Take second hit
    killed = enemy.take_hit()
    assert killed == False
    assert enemy.hp == 1
    
    # Take third hit (should die)
    killed = enemy.take_hit()
    assert killed == True
    assert enemy.hp == 0
    assert enemy.state == "dead"


def test_blunderbuss_firing():
    from game import GameWorld, Enemy
    from weapons import WEAPONS
    
    mock_sprites = {"walk1": None, "walk2": None, "hurt": None}
    world = GameWorld(enemy_sprites=mock_sprites)
    
    # Force state to PLAYING, reset weapon to blunderbuss
    world.state = "PLAYING"
    world.current_weapon = WEAPONS["blunderbuss"]
    
    # Place player at (9.5, 9.5) and cam_angle pointing along +X (0.0 rad)
    world.player_x = 9.5
    world.player_y = 9.5
    world.cam_angle = 0.0
    
    # Place enemy in front of player at distance of 5.0 (9.5 + 5.0, 9.5) = (14.5, 9.5)
    # The difference angle is 0.0, which is <= 0.96.
    # Enemy starts with 8 HP
    enemy1 = Enemy(x=14.5, y=9.5, hp=8, speed=1.0, sprites=mock_sprites)
    world.enemies = [enemy1]
    
    # Fire!
    hit, killed = world.fire()
    assert hit == enemy1
    assert killed == False
    assert enemy1.hp == 2  # Blunderbuss does 6 damage, so 8 - 6 = 2 HP remaining
    
    # Enemy is now hurt, let's verify state
    # Wait, enemy.state is set to "hurt"
    assert enemy1.state == "hurt"


def test_enemy_hurt_recovery():
    from game import Enemy
    mock_sprites = {"walk1": None, "walk2": None, "hurt": None}
    enemy = Enemy(x=0.0, y=0.0, hp=5, speed=1.0, sprites=mock_sprites)
    
    # Hit the enemy to put it in hurt state
    enemy.take_hit()
    assert enemy.state == "hurt"
    assert enemy.hurt_flash == 0.18
    
    # Update enemy with small dt (0.05s) - should still be in hurt state
    enemy.update(0.05, player_x=0.0, player_y=0.0, world_map=[])
    assert enemy.state == "hurt"
    assert abs(enemy.hurt_flash - 0.13) < 1e-5
    
    # Update with dt that completes hurt flash (0.15s) - should recover to walk1
    enemy.update(0.15, player_x=0.0, player_y=0.0, world_map=[])
    assert enemy.state == "walk1"
    assert enemy.hurt_flash == 0.0


def test_blunderbuss_multiple_enemies():
    from game import GameWorld, Enemy
    from weapons import WEAPONS
    
    mock_sprites = {"walk1": None, "walk2": None, "hurt": None}
    world = GameWorld(enemy_sprites=mock_sprites)
    world.state = "PLAYING"
    world.current_weapon = WEAPONS["blunderbuss"]
    world.player_x = 9.5
    world.player_y = 9.5
    world.cam_angle = 0.0
    
    # Place two enemies in front of the player, one closer (11.5) and one farther (14.5)
    # The blunderbuss should damage both but return the closer one
    enemy_close = Enemy(x=11.5, y=9.5, hp=8, speed=1.0, sprites=mock_sprites)
    enemy_far = Enemy(x=14.5, y=9.5, hp=8, speed=1.0, sprites=mock_sprites)
    world.enemies = [enemy_close, enemy_far]
    
    hit, killed = world.fire()
    # Closest should be returned
    assert hit == enemy_close
    assert killed == False
    
    # Both should be damaged by 6
    assert enemy_close.hp == 2
    assert enemy_far.hp == 2


def test_duck_grenades_initial_and_throw():
    from game import GameWorld
    mock_sprites = {"walk1": None, "walk2": None, "hurt": None}
    world = GameWorld(enemy_sprites=mock_sprites)
    
    # Verify initial grenade count and cooldown
    assert world.duck_grenades == 3
    assert world.grenade_cooldown == 0.0
    
    # Try throwing in intro state (should fail)
    assert world.state == "WAVE_INTRO"
    success = world.throw_grenade()
    assert success == False
    assert world.duck_grenades == 3
    
    # Change state to PLAYING and throw
    world.state = "PLAYING"
    success = world.throw_grenade()
    assert success == True
    assert world.duck_grenades == 2
    assert world.grenade_cooldown == 1.0
    assert len(world.projectiles) == 1
    
    # Try throwing on cooldown (should fail)
    success = world.throw_grenade()
    assert success == False
    assert world.duck_grenades == 2



