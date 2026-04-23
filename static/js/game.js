const TILE_SIZE = 40;
const GRID_SIZE = 13;
const CANVAS_SIZE = TILE_SIZE * GRID_SIZE;

const TILE = {
    EMPTY: 0,
    BRICK: 1,
    STEEL: 2,
    WATER: 3,
    GRASS: 4,
    BASE: 5,
    ICE: 6
};

const DIRECTION = {
    UP: 0,
    RIGHT: 1,
    DOWN: 2,
    LEFT: 3
};

const POWERUP = {
    HELMET: 0,
    CLOCK: 1,
    SHOVEL: 2,
    STAR: 3,
    BOMB: 4,
    TANK: 5
};

const ENEMY_TYPE = {
    NORMAL: 0,
    FAST: 1,
    ARMORED: 2,
    BONUS: 3
};

const COLORS = {
    PLAYER: '#4CAF50',
    PLAYER_LEVEL2: '#66BB6A',
    PLAYER_LEVEL3: '#81C784',
    PLAYER_LEVEL4: '#A5D6A7',
    ENEMY_NORMAL: '#f44336',
    ENEMY_FAST: '#4CAF50',
    ENEMY_ARMORED: '#E91E63',
    ENEMY_BONUS: '#FFD700',
    BRICK: '#8B4513',
    STEEL: '#808080',
    WATER: '#1e90ff',
    GRASS: '#228B22',
    BASE: '#ffcc00',
    ICE: '#E0FFFF',
    BULLET: '#fff',
    POWERUP_HELMET: '#FFD700',
    POWERUP_CLOCK: '#00BCD4',
    POWERUP_SHOVEL: '#795548',
    POWERUP_STAR: '#FF9800',
    POWERUP_BOMB: '#F44336',
    POWERUP_TANK: '#4CAF50'
};

const LEVELS = [
    {
        name: "第一关",
        enemies: 10,
        map: [
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,1,1,0,0,0,0,0,1,1,0,0],
            [0,0,1,1,0,0,0,0,0,1,1,0,0],
            [0,0,1,1,0,0,1,1,0,1,1,0,0],
            [0,0,1,1,0,2,2,2,2,0,1,1,0,0],
            [0,3,0,0,0,2,2,2,2,0,0,0,3],
            [0,3,0,0,0,0,1,1,0,0,0,0,3],
            [0,3,0,1,1,0,1,1,0,1,1,0,3],
            [0,0,0,1,1,0,0,0,0,1,1,0,0],
            [0,0,0,0,0,0,4,4,0,0,0,0,0],
            [0,0,0,0,0,0,4,4,0,0,0,0,0],
            [0,0,0,0,0,1,5,1,0,0,0,0,0]
        ]
    },
    {
        name: "第二关",
        enemies: 14,
        map: [
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,2,2,0,0,2,2,2,0,0,2,2,0],
            [0,2,2,0,0,2,2,2,0,0,2,2,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,1,1,1,0,0,0,1,1,1,0,0],
            [0,0,1,1,1,0,0,0,1,1,1,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [1,1,0,0,2,2,2,2,2,0,0,1,1],
            [1,1,0,0,2,2,2,2,2,0,0,1,1],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,4,4,0,0,0,0,4,4,0,0],
            [0,0,0,4,4,0,0,0,0,4,4,0,0],
            [0,0,0,0,0,1,5,1,0,0,0,0,0]
        ]
    },
    {
        name: "第三关",
        enemies: 18,
        map: [
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,0,1,0,1,0,1,0,1,0,1,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,0,1,0,1,0,1,0,1,0,1,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,0,1,0,1,0,1,0,1,0,1,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,0,1,0,1,0,1,0,1,0,1,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,1,0,1,0,1,0,1,0,1,0,1,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,1,5,1,0,0,0,0,0]
        ]
    },
    {
        name: "第四关",
        enemies: 20,
        map: [
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,6,6,6,0,0,0,0,0,6,6,6,0],
            [0,6,6,6,0,0,0,0,0,6,6,6,0],
            [0,6,6,6,0,3,3,3,0,6,6,6,0],
            [0,0,0,0,0,3,3,3,0,0,0,0,0],
            [2,2,0,0,0,0,0,0,0,0,0,2,2],
            [2,2,0,1,1,0,0,0,1,1,0,2,2],
            [0,0,0,1,1,0,0,0,1,1,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,4,4,0,0,0,4,4,0,0,0],
            [0,0,0,4,4,0,0,0,4,4,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,1,5,1,0,0,0,0,0]
        ]
    },
    {
        name: "第五关",
        enemies: 24,
        map: [
            [2,2,0,2,2,0,0,0,2,2,0,2,2],
            [2,2,0,2,2,0,0,0,2,2,0,2,2],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,1,1,1,1,1,1,1,0,0,0],
            [0,0,0,1,0,0,0,0,0,1,0,0,0],
            [0,0,0,1,0,2,2,2,0,1,0,0,0],
            [3,3,0,1,0,2,2,2,0,1,0,3,3],
            [3,3,0,1,0,0,0,0,0,1,0,3,3],
            [0,0,0,1,1,1,0,1,1,1,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,4,4,0,0,0,0,0,4,4,0,0],
            [0,0,4,4,0,0,0,0,0,4,4,0,0],
            [0,0,0,0,0,1,5,1,0,0,0,0,0]
        ]
    }
];

class SoundManager {
    constructor() {
        this.audioContext = null;
        this.enabled = true;
        this.init();
    }
    
    init() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext();
        } catch (e) {
            console.log('Web Audio API not supported');
            this.enabled = false;
        }
    }
    
    playTone(frequency, duration, type = 'square', volume = 0.1) {
        if (!this.enabled || !this.audioContext) return;
        
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.type = type;
        oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);
        
        gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration);
    }
    
    playShoot() {
        this.playTone(800, 0.05, 'square', 0.08);
    }
    
    playExplosion() {
        this.playTone(150, 0.2, 'sawtooth', 0.15);
        setTimeout(() => this.playTone(100, 0.3, 'sawtooth', 0.12), 50);
    }
    
    playPowerup() {
        this.playTone(523, 0.1, 'sine', 0.1);
        setTimeout(() => this.playTone(659, 0.1, 'sine', 0.1), 100);
        setTimeout(() => this.playTone(784, 0.15, 'sine', 0.1), 200);
    }
    
    playGameStart() {
        this.playTone(392, 0.15, 'square', 0.1);
        setTimeout(() => this.playTone(523, 0.15, 'square', 0.1), 150);
        setTimeout(() => this.playTone(659, 0.15, 'square', 0.1), 300);
        setTimeout(() => this.playTone(784, 0.3, 'square', 0.1), 450);
    }
    
    playGameOver() {
        this.playTone(392, 0.3, 'square', 0.1);
        setTimeout(() => this.playTone(349, 0.3, 'square', 0.1), 300);
        setTimeout(() => this.playTone(330, 0.3, 'square', 0.1), 600);
        setTimeout(() => this.playTone(262, 0.5, 'square', 0.1), 900);
    }
    
    playLevelComplete() {
        const notes = [523, 587, 659, 698, 784, 880, 988, 1047];
        notes.forEach((note, i) => {
            setTimeout(() => this.playTone(note, 0.15, 'square', 0.08), i * 100);
        });
    }
    
    playMove() {
        this.playTone(100, 0.02, 'square', 0.03);
    }
}

class Game {
    constructor() {
        this.canvas = document.getElementById('gameCanvas');
        this.ctx = this.canvas.getContext('2d');
        this.overlay = document.getElementById('gameOverlay');
        this.overlayTitle = document.getElementById('overlayTitle');
        this.overlayMessage = document.getElementById('overlayMessage');
        
        this.levelElement = document.getElementById('level');
        this.scoreElement = document.getElementById('score');
        this.livesElement = document.getElementById('lives');
        this.enemiesLeftElement = document.getElementById('enemiesLeft');
        
        this.soundManager = new SoundManager();
        
        this.state = 'start';
        this.level = 1;
        this.score = 0;
        this.lives = 3;
        
        this.player = null;
        this.enemies = [];
        this.bullets = [];
        this.map = [];
        this.explosions = [];
        this.powerups = [];
        
        this.keys = {};
        
        this.maxEnemies = 4;
        this.enemiesRemaining = 10;
        this.enemiesSpawned = 0;
        this.enemySpawnTimer = 0;
        this.enemySpawnInterval = 3000;
        
        this.freezeTimer = 0;
        this.freezeDuration = 10000;
        
        this.invincibleTimer = 0;
        this.invincibleDuration = 5000;
        
        this.baseProtected = false;
        this.baseProtectionTimer = 0;
        this.baseProtectionDuration = 15000;
        
        this.moveSoundTimer = 0;
        this.moveSoundInterval = 100;
        
        this.powerupSpawnTimer = 0;
        this.powerupSpawnInterval = 20000;
        this.powerupSpawnChance = 0.3;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.loadLevel(this.level);
        this.spawnPlayer();
        this.updateUI();
        this.showOverlay('游戏开始', '按空格键开始游戏');
        this.gameLoop();
    }
    
    bindEvents() {
        document.addEventListener('keydown', (e) => {
            this.keys[e.code] = true;
            
            if (e.code === 'Space') {
                e.preventDefault();
                if (this.state === 'start' || this.state === 'gameover' || this.state === 'win') {
                    this.startGame();
                } else if (this.state === 'paused') {
                    this.resumeGame();
                } else if (this.state === 'levelComplete') {
                    this.nextLevel();
                }
            }
            
            if (e.code === 'KeyP' && this.state === 'playing') {
                this.pauseGame();
            }
        });
        
        document.addEventListener('keyup', (e) => {
            this.keys[e.code] = false;
        });
    }
    
    loadLevel(levelNum) {
        const levelIndex = (levelNum - 1) % LEVELS.length;
        const levelData = LEVELS[levelIndex];
        
        this.map = levelData.map.map(row => [...row]);
        this.enemiesRemaining = levelData.enemies;
        this.enemiesSpawned = 0;
        
        this.enemies = [];
        this.bullets = [];
        this.explosions = [];
        this.powerups = [];
    }
    
    spawnPlayer() {
        this.player = new Tank(
            TILE_SIZE * 4,
            CANVAS_SIZE - TILE_SIZE,
            DIRECTION.UP,
            COLORS.PLAYER,
            true,
            ENEMY_TYPE.NORMAL
        );
        this.player.invincible = true;
        this.invincibleTimer = Date.now();
    }
    
    spawnEnemy() {
        if (this.enemies.length >= this.maxEnemies || this.enemiesRemaining <= 0) return;
        
        const spawnPoints = [
            { x: 0, y: 0 },
            { x: TILE_SIZE * 6, y: 0 },
            { x: CANVAS_SIZE - TILE_SIZE, y: 0 }
        ];
        
        const spawn = spawnPoints[Math.floor(Math.random() * spawnPoints.length)];
        
        const blocked = this.enemies.some(enemy => 
            Math.abs(enemy.x - spawn.x) < TILE_SIZE && Math.abs(enemy.y - spawn.y) < TILE_SIZE
        );
        
        if (blocked) return;
        
        let enemyType;
        const rand = Math.random();
        if (rand < 0.1 && this.enemiesSpawned > 3) {
            enemyType = ENEMY_TYPE.BONUS;
        } else if (rand < 0.25) {
            enemyType = ENEMY_TYPE.ARMORED;
        } else if (rand < 0.5) {
            enemyType = ENEMY_TYPE.FAST;
        } else {
            enemyType = ENEMY_TYPE.NORMAL;
        }
        
        let color, hp, speed;
        switch (enemyType) {
            case ENEMY_TYPE.FAST:
                color = COLORS.ENEMY_FAST;
                hp = 1;
                speed = 2.5;
                break;
            case ENEMY_TYPE.ARMORED:
                color = COLORS.ENEMY_ARMORED;
                hp = 4;
                speed = 1;
                break;
            case ENEMY_TYPE.BONUS:
                color = COLORS.ENEMY_BONUS;
                hp = 1;
                speed = 1.5;
                break;
            default:
                color = COLORS.ENEMY_NORMAL;
                hp = 1;
                speed = 1.5;
        }
        
        const enemy = new Tank(
            spawn.x,
            spawn.y,
            DIRECTION.DOWN,
            color,
            false,
            enemyType
        );
        enemy.hp = hp;
        enemy.maxHp = hp;
        enemy.speed = speed;
        
        enemy.spawning = true;
        enemy.spawnTimer = Date.now();
        enemy.spawnDuration = 1000;
        
        this.enemies.push(enemy);
        this.enemiesRemaining--;
        this.enemiesSpawned++;
        this.updateUI();
    }
    
    spawnPowerup(x, y) {
        const types = Object.values(POWERUP);
        const type = types[Math.floor(Math.random() * types.length)];
        
        let color, symbol;
        switch (type) {
            case POWERUP.HELMET:
                color = COLORS.POWERUP_HELMET;
                symbol = '🛡';
                break;
            case POWERUP.CLOCK:
                color = COLORS.POWERUP_CLOCK;
                symbol = '⏱';
                break;
            case POWERUP.SHOVEL:
                color = COLORS.POWERUP_SHOVEL;
                symbol = '⛏';
                break;
            case POWERUP.STAR:
                color = COLORS.POWERUP_STAR;
                symbol = '★';
                break;
            case POWERUP.BOMB:
                color = COLORS.POWERUP_BOMB;
                symbol = '💣';
                break;
            case POWERUP.TANK:
                color = COLORS.POWERUP_TANK;
                symbol = '🎖';
                break;
        }
        
        this.powerups.push({
            x: x,
            y: y,
            type: type,
            color: color,
            symbol: symbol,
            size: TILE_SIZE - 8,
            flashTimer: 0,
            visible: true
        });
    }
    
    collectPowerup(powerup) {
        this.soundManager.playPowerup();
        this.score += 500;
        this.updateUI();
        
        switch (powerup.type) {
            case POWERUP.HELMET:
                this.player.invincible = true;
                this.invincibleTimer = Date.now();
                break;
                
            case POWERUP.CLOCK:
                this.freezeTimer = Date.now();
                break;
                
            case POWERUP.SHOVEL:
                this.protectBase();
                break;
                
            case POWERUP.STAR:
                this.player.levelUp();
                break;
                
            case POWERUP.BOMB:
                this.destroyAllEnemies();
                break;
                
            case POWERUP.TANK:
                this.lives++;
                this.updateUI();
                break;
        }
        
        this.powerups = this.powerups.filter(p => p !== powerup);
    }
    
    protectBase() {
        this.baseProtected = true;
        this.baseProtectionTimer = Date.now();
        
        const baseX = 6;
        const baseY = 12;
        
        const positions = [
            {x: baseX - 1, y: baseY - 1},
            {x: baseX, y: baseY - 1},
            {x: baseX + 1, y: baseY - 1},
            {x: baseX - 1, y: baseY},
            {x: baseX + 1, y: baseY}
        ];
        
        positions.forEach(pos => {
            if (pos.x >= 0 && pos.x < GRID_SIZE && pos.y >= 0 && pos.y < GRID_SIZE) {
                if (this.map[pos.y][pos.x] === TILE.BRICK || this.map[pos.y][pos.x] === TILE.EMPTY) {
                    this.map[pos.y][pos.x] = TILE.STEEL;
                }
            }
        });
    }
    
    unprotectBase() {
        if (!this.baseProtected) return;
        this.baseProtected = false;
        
        const baseX = 6;
        const baseY = 12;
        
        const positions = [
            {x: baseX - 1, y: baseY - 1},
            {x: baseX, y: baseY - 1},
            {x: baseX + 1, y: baseY - 1},
            {x: baseX - 1, y: baseY},
            {x: baseX + 1, y: baseY}
        ];
        
        positions.forEach(pos => {
            if (pos.x >= 0 && pos.x < GRID_SIZE && pos.y >= 0 && pos.y < GRID_SIZE) {
                if (this.map[pos.y][pos.x] === TILE.STEEL) {
                    this.map[pos.y][pos.x] = TILE.BRICK;
                }
            }
        });
    }
    
    destroyAllEnemies() {
        this.enemies.forEach(enemy => {
            if (!enemy.spawning) {
                this.createExplosion(enemy.x + enemy.size / 2, enemy.y + enemy.size / 2, true);
                this.score += 100;
            }
        });
        this.enemies = [];
        this.soundManager.playExplosion();
        this.updateUI();
    }
    
    startGame() {
        if (this.state === 'gameover') {
            this.level = 1;
            this.score = 0;
            this.lives = 3;
            this.loadLevel(this.level);
            this.spawnPlayer();
        }
        
        this.state = 'playing';
        this.hideOverlay();
        this.enemySpawnTimer = Date.now();
        this.powerupSpawnTimer = Date.now();
        this.soundManager.playGameStart();
    }
    
    pauseGame() {
        this.state = 'paused';
        this.showOverlay('游戏暂停', '按空格键继续游戏');
    }
    
    resumeGame() {
        this.state = 'playing';
        this.hideOverlay();
    }
    
    levelComplete() {
        this.state = 'levelComplete';
        this.soundManager.playLevelComplete();
        this.showOverlay('关卡 ' + this.level + ' 通过!', '得分: ' + this.score + ' - 按空格键继续');
    }
    
    nextLevel() {
        this.level++;
        this.loadLevel(this.level);
        this.spawnPlayer();
        this.updateUI();
        this.hideOverlay();
        this.state = 'playing';
        this.enemySpawnTimer = Date.now();
        this.powerupSpawnTimer = Date.now();
    }
    
    gameOver(win = false) {
        this.state = win ? 'win' : 'gameover';
        if (win) {
            this.showOverlay('恭喜通关!', '最终得分: ' + this.score + ' - 按空格键重新开始');
        } else {
            this.soundManager.playGameOver();
            this.showOverlay('游戏结束', '最终得分: ' + this.score + ' - 按空格键重新开始');
        }
    }
    
    showOverlay(title, message) {
        this.overlayTitle.textContent = title;
        this.overlayMessage.textContent = message;
        this.overlay.classList.remove('hidden');
    }
    
    hideOverlay() {
        this.overlay.classList.add('hidden');
    }
    
    updateUI() {
        this.levelElement.textContent = this.level;
        this.scoreElement.textContent = this.score;
        this.livesElement.textContent = this.lives;
        if (this.enemiesLeftElement) {
            this.enemiesLeftElement.textContent = this.enemiesRemaining + this.enemies.length;
        }
    }
    
    handleInput() {
        if (this.state !== 'playing' || !this.player) return;
        
        let moved = false;
        let onIce = false;
        
        const playerCenterX = this.player.x + this.player.size / 2;
        const playerCenterY = this.player.y + this.player.size / 2;
        const gridX = Math.floor(playerCenterX / TILE_SIZE);
        const gridY = Math.floor(playerCenterY / TILE_SIZE);
        
        if (gridX >= 0 && gridX < GRID_SIZE && gridY >= 0 && gridY < GRID_SIZE) {
            onIce = this.map[gridY][gridX] === TILE.ICE;
        }
        
        if (this.keys['KeyW'] || this.keys['ArrowUp']) {
            this.player.direction = DIRECTION.UP;
            if (onIce) {
                this.player.iceSlideDx = 0;
                this.player.iceSlideDy = -this.player.speed;
            } else {
                moved = this.tryMoveTank(this.player, 0, -this.player.speed);
            }
        } else if (this.keys['KeyS'] || this.keys['ArrowDown']) {
            this.player.direction = DIRECTION.DOWN;
            if (onIce) {
                this.player.iceSlideDx = 0;
                this.player.iceSlideDy = this.player.speed;
            } else {
                moved = this.tryMoveTank(this.player, 0, this.player.speed);
            }
        } else if (this.keys['KeyA'] || this.keys['ArrowLeft']) {
            this.player.direction = DIRECTION.LEFT;
            if (onIce) {
                this.player.iceSlideDx = -this.player.speed;
                this.player.iceSlideDy = 0;
            } else {
                moved = this.tryMoveTank(this.player, -this.player.speed, 0);
            }
        } else if (this.keys['KeyD'] || this.keys['ArrowRight']) {
            this.player.direction = DIRECTION.RIGHT;
            if (onIce) {
                this.player.iceSlideDx = this.player.speed;
                this.player.iceSlideDy = 0;
            } else {
                moved = this.tryMoveTank(this.player, this.player.speed, 0);
            }
        }
        
        if (onIce && this.player.iceSlideDx !== undefined) {
            if (this.player.iceSlideDx !== 0 || this.player.iceSlideDy !== 0) {
                if (!this.tryMoveTank(this.player, this.player.iceSlideDx, this.player.iceSlideDy)) {
                    this.player.iceSlideDx = 0;
                    this.player.iceSlideDy = 0;
                }
            }
        }
        
        if (moved) {
            const now = Date.now();
            if (now - this.moveSoundTimer > this.moveSoundInterval) {
                this.soundManager.playMove();
                this.moveSoundTimer = now;
            }
        }
        
        const now = Date.now();
        if (this.keys['Space'] && now - this.player.lastShotTime > this.player.shootCooldown) {
            const bullets = this.player.createBullets();
            bullets.forEach(bullet => this.bullets.push(bullet));
            if (bullets.length > 0) {
                this.soundManager.playShoot();
            }
        }
    }
    
    tryMoveTank(tank, dx, dy) {
        const newX = tank.x + dx;
        const newY = tank.y + dy;
        
        if (this.checkCollision(newX, newY, tank.size, tank)) {
            return false;
        }
        
        tank.x = newX;
        tank.y = newY;
        return true;
    }
    
    checkCollision(x, y, size, excludeTank = null) {
        if (x < 0 || x + size > CANVAS_SIZE || y < 0 || y + size > CANVAS_SIZE) {
            return true;
        }
        
        const left = Math.floor(x / TILE_SIZE);
        const right = Math.floor((x + size - 1) / TILE_SIZE);
        const top = Math.floor(y / TILE_SIZE);
        const bottom = Math.floor((y + size - 1) / TILE_SIZE);
        
        for (let ty = top; ty <= bottom; ty++) {
            for (let tx = left; tx <= right; tx++) {
                if (ty >= 0 && ty < GRID_SIZE && tx >= 0 && tx < GRID_SIZE) {
                    const tile = this.map[ty][tx];
                    if (tile === TILE.BRICK || tile === TILE.STEEL || tile === TILE.WATER || tile === TILE.BASE) {
                        return true;
                    }
                }
            }
        }
        
        const tanks = [this.player, ...this.enemies].filter(t => t && t !== excludeTank);
        for (const tank of tanks) {
            if (this.rectsIntersect(x, y, size, size, tank.x, tank.y, tank.size, tank.size)) {
                return true;
            }
        }
        
        return false;
    }
    
    rectsIntersect(x1, y1, w1, h1, x2, y2, w2, h2) {
        return x1 < x2 + w2 && x1 + w1 > x2 && y1 < y2 + h2 && y1 + h1 > y2;
    }
    
    updateEnemies() {
        if (this.state !== 'playing') return;
        
        const now = Date.now();
        
        if (this.baseProtected && now - this.baseProtectionTimer > this.baseProtectionDuration) {
            this.unprotectBase();
        }
        
        if (this.player && this.player.invincible && now - this.invincibleTimer > this.invincibleDuration) {
            this.player.invincible = false;
        }
        
        const frozen = now - this.freezeTimer < this.freezeDuration;
        
        if (now - this.enemySpawnTimer > this.enemySpawnInterval) {
            this.spawnEnemy();
            this.enemySpawnTimer = now;
        }
        
        for (let i = this.enemies.length - 1; i >= 0; i--) {
            const enemy = this.enemies[i];
            
            if (enemy.spawning) {
                if (now - enemy.spawnTimer > enemy.spawnDuration) {
                    enemy.spawning = false;
                }
                continue;
            }
            
            if (frozen) continue;
            
            enemy.updateAI();
            
            let dx = 0;
            let dy = 0;
            
            switch (enemy.direction) {
                case DIRECTION.UP: dy = -enemy.speed; break;
                case DIRECTION.DOWN: dy = enemy.speed; break;
                case DIRECTION.LEFT: dx = -enemy.speed; break;
                case DIRECTION.RIGHT: dx = enemy.speed; break;
            }
            
            if (!this.tryMoveTank(enemy, dx, dy)) {
                enemy.changeDirection();
            }
            
            if (enemy.shouldShoot()) {
                const bullets = enemy.createBullets();
                bullets.forEach(bullet => this.bullets.push(bullet));
            }
        }
        
        if (this.enemies.length === 0 && this.enemiesRemaining === 0) {
            this.levelComplete();
        }
    }
    
    updateBullets() {
        this.bullets.forEach(bullet => bullet.update());
        
        const bulletsToRemove = new Set();
        
        const playerBullets = this.bullets.filter(b => b.isPlayerBullet);
        const enemyBullets = this.bullets.filter(b => !b.isPlayerBullet);
        
        for (let i = 0; i < playerBullets.length; i++) {
            for (let j = 0; j < enemyBullets.length; j++) {
                const pBullet = playerBullets[i];
                const eBullet = enemyBullets[j];
                
                if (this.bulletsIntersect(pBullet, eBullet)) {
                    bulletsToRemove.add(pBullet);
                    bulletsToRemove.add(eBullet);
                    this.createExplosion(
                        (pBullet.x + eBullet.x) / 2,
                        (pBullet.y + eBullet.y) / 2,
                        false
                    );
                }
            }
        }
        
        this.bullets = this.bullets.filter(bullet => {
            if (bulletsToRemove.has(bullet)) {
                return false;
            }
            
            if (bullet.x < 0 || bullet.x > CANVAS_SIZE || bullet.y < 0 || bullet.y > CANVAS_SIZE) {
                return false;
            }
            
            const gridX = Math.floor(bullet.x / TILE_SIZE);
            const gridY = Math.floor(bullet.y / TILE_SIZE);
            
            if (gridX >= 0 && gridX < GRID_SIZE && gridY >= 0 && gridY < GRID_SIZE) {
                const tile = this.map[gridY][gridX];
                
                if (tile === TILE.BRICK) {
                    this.map[gridY][gridX] = TILE.EMPTY;
                    this.createExplosion(bullet.x, bullet.y);
                    this.soundManager.playExplosion();
                    return false;
                }
                
                if (tile === TILE.STEEL) {
                    if (bullet.canDestroySteel) {
                        this.map[gridY][gridX] = TILE.EMPTY;
                    }
                    this.createExplosion(bullet.x, bullet.y, false);
                    this.soundManager.playExplosion();
                    return false;
                }
                
                if (tile === TILE.BASE) {
                    this.map[gridY][gridX] = TILE.EMPTY;
                    this.createExplosion(bullet.x, bullet.y, true);
                    this.soundManager.playExplosion();
                    this.gameOver(false);
                    return false;
                }
            }
            
            if (bullet.isPlayerBullet) {
                for (let i = this.enemies.length - 1; i >= 0; i--) {
                    const enemy = this.enemies[i];
                    if (enemy.spawning) continue;
                    
                    if (this.rectsIntersect(
                        bullet.x - bullet.size / 2, bullet.y - bullet.size / 2, bullet.size, bullet.size,
                        enemy.x, enemy.y, enemy.size, enemy.size
                    )) {
                        enemy.hp--;
                        
                        if (enemy.hp <= 0) {
                            this.enemies.splice(i, 1);
                            this.score += enemy.type === ENEMY_TYPE.ARMORED ? 400 : 100;
                            this.createExplosion(enemy.x + enemy.size / 2, enemy.y + enemy.size / 2, true);
                            this.soundManager.playExplosion();
                            this.updateUI();
                            
                            if (enemy.type === ENEMY_TYPE.BONUS) {
                                this.spawnPowerup(enemy.x, enemy.y);
                            }
                        } else {
                            this.createExplosion(bullet.x, bullet.y, false);
                        }
                        return false;
                    }
                }
            } else {
                if (this.player && !this.player.invincible && this.rectsIntersect(
                    bullet.x - bullet.size / 2, bullet.y - bullet.size / 2, bullet.size, bullet.size,
                    this.player.x, this.player.y, this.player.size, this.player.size
                )) {
                    this.lives--;
                    this.createExplosion(this.player.x + this.player.size / 2, this.player.y + this.player.size / 2, true);
                    this.soundManager.playExplosion();
                    this.updateUI();
                    
                    if (this.lives <= 0) {
                        this.gameOver(false);
                    } else {
                        this.spawnPlayer();
                    }
                    return false;
                }
            }
            
            return true;
        });
    }
    
    updatePowerups() {
        if (!this.player) return;
        
        this.powerups.forEach(powerup => {
            powerup.flashTimer++;
            if (powerup.flashTimer % 10 === 0) {
                powerup.visible = !powerup.visible;
            }
            
            if (this.rectsIntersect(
                powerup.x, powerup.y, powerup.size, powerup.size,
                this.player.x, this.player.y, this.player.size, this.player.size
            )) {
                this.collectPowerup(powerup);
            }
        });
    }
    
    updatePowerupSpawn() {
        if (this.state !== 'playing') return;
        
        const now = Date.now();
        if (now - this.powerupSpawnTimer >= this.powerupSpawnInterval) {
            this.powerupSpawnTimer = now;
            
            if (Math.random() < this.powerupSpawnChance) {
                this.spawnRandomPowerup();
            }
        }
    }
    
    spawnRandomPowerup() {
        const emptyPositions = [];
        
        for (let y = 0; y < GRID_SIZE; y++) {
            for (let x = 0; x < GRID_SIZE; x++) {
                if (this.map[y][x] === TILE.EMPTY) {
                    emptyPositions.push({ x: x, y: y });
                }
            }
        }
        
        if (emptyPositions.length === 0) return;
        
        const pos = emptyPositions[Math.floor(Math.random() * emptyPositions.length)];
        const px = pos.x * TILE_SIZE + (TILE_SIZE - (TILE_SIZE - 8)) / 2;
        const py = pos.y * TILE_SIZE + (TILE_SIZE - (TILE_SIZE - 8)) / 2;
        
        this.spawnPowerup(px, py);
    }
    
    bulletsIntersect(bullet1, bullet2) {
        const dx = bullet1.x - bullet2.x;
        const dy = bullet1.y - bullet2.y;
        const distance = Math.sqrt(dx * dx + dy * dy);
        return distance < (bullet1.size + bullet2.size) / 2;
    }
    
    createExplosion(x, y, large = true) {
        this.explosions.push({
            x: x,
            y: y,
            size: large ? 40 : 20,
            frame: 0,
            maxFrames: large ? 15 : 10
        });
    }
    
    updateExplosions() {
        this.explosions = this.explosions.filter(exp => {
            exp.frame++;
            return exp.frame < exp.maxFrames;
        });
    }
    
    draw() {
        this.ctx.fillStyle = '#000';
        this.ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
        
        this.drawMap();
        
        this.powerups.forEach(powerup => {
            if (powerup.visible) {
                this.drawPowerup(powerup);
            }
        });
        
        if (this.player) {
            this.drawTank(this.player);
        }
        
        this.enemies.forEach(enemy => {
            if (enemy.spawning) {
                this.drawSpawningTank(enemy);
            } else {
                this.drawTank(enemy);
            }
        });
        
        this.bullets.forEach(bullet => this.drawBullet(bullet));
        
        this.drawExplosions();
        
        this.drawGrassOverlay();
        
        this.drawStatusIndicators();
    }
    
    drawStatusIndicators() {
        const now = Date.now();
        
        if (this.player && this.player.invincible) {
            const remaining = Math.ceil((this.invincibleDuration - (now - this.invincibleTimer)) / 1000);
            this.ctx.fillStyle = 'rgba(255, 215, 0, 0.3)';
            this.ctx.fillRect(this.player.x - 2, this.player.y - 2, this.player.size + 4, this.player.size + 4);
        }
        
        if (now - this.freezeTimer < this.freezeDuration) {
            this.ctx.fillStyle = 'rgba(0, 188, 212, 0.2)';
            this.ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
        }
    }
    
    drawMap() {
        for (let y = 0; y < GRID_SIZE; y++) {
            for (let x = 0; x < GRID_SIZE; x++) {
                const tile = this.map[y][x];
                const px = x * TILE_SIZE;
                const py = y * TILE_SIZE;
                
                switch (tile) {
                    case TILE.BRICK:
                        this.drawBrick(px, py);
                        break;
                    case TILE.STEEL:
                        this.drawSteel(px, py);
                        break;
                    case TILE.WATER:
                        this.drawWater(px, py);
                        break;
                    case TILE.GRASS:
                        this.drawGrass(px, py);
                        break;
                    case TILE.BASE:
                        this.drawBase(px, py);
                        break;
                    case TILE.ICE:
                        this.drawIce(px, py);
                        break;
                }
            }
        }
    }
    
    drawBrick(x, y) {
        this.ctx.fillStyle = COLORS.BRICK;
        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        this.ctx.strokeStyle = '#5a3010';
        this.ctx.lineWidth = 2;
        
        this.ctx.beginPath();
        this.ctx.moveTo(x, y + TILE_SIZE / 2);
        this.ctx.lineTo(x + TILE_SIZE, y + TILE_SIZE / 2);
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.moveTo(x + TILE_SIZE / 2, y);
        this.ctx.lineTo(x + TILE_SIZE / 2, y + TILE_SIZE / 2);
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.moveTo(x + TILE_SIZE / 4, y + TILE_SIZE / 2);
        this.ctx.lineTo(x + TILE_SIZE / 4, y + TILE_SIZE);
        this.ctx.stroke();
        
        this.ctx.beginPath();
        this.ctx.moveTo(x + TILE_SIZE * 3 / 4, y + TILE_SIZE / 2);
        this.ctx.lineTo(x + TILE_SIZE * 3 / 4, y + TILE_SIZE);
        this.ctx.stroke();
    }
    
    drawSteel(x, y) {
        const gradient = this.ctx.createLinearGradient(x, y, x + TILE_SIZE, y + TILE_SIZE);
        gradient.addColorStop(0, '#ccc');
        gradient.addColorStop(0.5, '#999');
        gradient.addColorStop(1, '#666');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        this.ctx.strokeStyle = '#555';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4);
        
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        this.ctx.fillRect(x + 4, y + 4, TILE_SIZE - 8, 4);
    }
    
    drawWater(x, y) {
        const gradient = this.ctx.createLinearGradient(x, y, x, y + TILE_SIZE);
        gradient.addColorStop(0, '#4169e1');
        gradient.addColorStop(1, '#1e90ff');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
        this.ctx.lineWidth = 1;
        
        const time = Date.now() / 200;
        for (let i = 0; i < 3; i++) {
            const offset = Math.sin(time + i) * 3;
            this.ctx.beginPath();
            this.ctx.arc(x + TILE_SIZE / 4 + i * 12 + offset, y + TILE_SIZE / 2, 5, 0, Math.PI);
            this.ctx.stroke();
        }
    }
    
    drawGrass(x, y) {
        this.ctx.fillStyle = COLORS.GRASS;
        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        this.ctx.fillStyle = '#1a5c1a';
        for (let i = 0; i < 8; i++) {
            const gx = x + 5 + Math.random() * (TILE_SIZE - 10);
            const gy = y + 5 + Math.random() * (TILE_SIZE - 10);
            this.ctx.fillRect(gx, gy, 2, 8);
        }
    }
    
    drawIce(x, y) {
        this.ctx.fillStyle = COLORS.ICE;
        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        this.ctx.fillRect(x + 5, y + 5, 8, 3);
        this.ctx.fillRect(x + 25, y + 15, 10, 3);
        this.ctx.fillRect(x + 10, y + 28, 12, 3);
        
        this.ctx.strokeStyle = 'rgba(200, 200, 255, 0.3)';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(x + 1, y + 1, TILE_SIZE - 2, TILE_SIZE - 2);
    }
    
    drawBase(x, y) {
        this.ctx.fillStyle = '#8B4513';
        this.ctx.fillRect(x + 5, y + 5, TILE_SIZE - 10, TILE_SIZE - 10);
        
        this.ctx.fillStyle = COLORS.BASE;
        this.ctx.beginPath();
        this.ctx.moveTo(x + TILE_SIZE / 2, y + 8);
        this.ctx.lineTo(x + TILE_SIZE - 8, y + TILE_SIZE - 8);
        this.ctx.lineTo(x + 8, y + TILE_SIZE - 8);
        this.ctx.closePath();
        this.ctx.fill();
        
        this.ctx.fillStyle = '#ff6600';
        this.ctx.beginPath();
        this.ctx.arc(x + TILE_SIZE / 2, y + TILE_SIZE / 2, 5, 0, Math.PI * 2);
        this.ctx.fill();
        
        const pulse = Math.sin(Date.now() / 200) * 0.3 + 0.7;
        this.ctx.strokeStyle = `rgba(255, 102, 0, ${pulse})`;
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.arc(x + TILE_SIZE / 2, y + TILE_SIZE / 2, 8 + pulse * 2, 0, Math.PI * 2);
        this.ctx.stroke();
    }
    
    drawGrassOverlay() {
        this.ctx.globalAlpha = 0.7;
        for (let y = 0; y < GRID_SIZE; y++) {
            for (let x = 0; x < GRID_SIZE; x++) {
                if (this.map[y][x] === TILE.GRASS) {
                    const px = x * TILE_SIZE;
                    const py = y * TILE_SIZE;
                    this.ctx.fillStyle = COLORS.GRASS;
                    this.ctx.fillRect(px, py, TILE_SIZE, TILE_SIZE);
                }
            }
        }
        this.ctx.globalAlpha = 1.0;
    }
    
    drawPowerup(powerup) {
        const x = powerup.x;
        const y = powerup.y;
        const size = powerup.size;
        
        this.ctx.fillStyle = powerup.color;
        this.ctx.fillRect(x, y, size, size);
        
        this.ctx.strokeStyle = '#fff';
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(x, y, size, size);
        
        this.ctx.fillStyle = '#fff';
        this.ctx.font = 'bold 20px Arial';
        this.ctx.textAlign = 'center';
        this.ctx.textBaseline = 'middle';
        this.ctx.fillText(powerup.symbol, x + size / 2, y + size / 2);
    }
    
    drawSpawningTank(tank) {
        const now = Date.now();
        const elapsed = now - tank.spawnTimer;
        const progress = elapsed / tank.spawnDuration;
        
        const x = tank.x + tank.size / 2;
        const y = tank.y + tank.size / 2;
        
        const flash = Math.sin(now / 50) > 0;
        
        if (flash) {
            this.ctx.fillStyle = '#fff';
            this.ctx.beginPath();
            this.ctx.arc(x, y, tank.size / 2, 0, Math.PI * 2);
            this.ctx.fill();
        }
        
        const starAngle = (now / 100) % (Math.PI * 2);
        for (let i = 0; i < 4; i++) {
            const angle = starAngle + i * Math.PI / 2;
            const radius = tank.size / 2 * (1 - progress * 0.5);
            const sx = x + Math.cos(angle) * radius;
            const sy = y + Math.sin(angle) * radius;
            
            this.ctx.fillStyle = '#ff0';
            this.ctx.beginPath();
            this.ctx.arc(sx, sy, 4, 0, Math.PI * 2);
            this.ctx.fill();
        }
    }
    
    drawTank(tank) {
        this.ctx.save();
        this.ctx.translate(tank.x + tank.size / 2, tank.y + tank.size / 2);
        
        const angle = tank.direction * Math.PI / 2;
        this.ctx.rotate(angle);
        
        if (tank.invincible) {
            const flash = Math.sin(Date.now() / 100) > 0;
            if (flash) {
                this.ctx.strokeStyle = '#ff0';
                this.ctx.lineWidth = 3;
                this.ctx.strokeRect(-tank.size / 2 - 2, -tank.size / 2 - 2, tank.size + 4, tank.size + 4);
            }
        }
        
        this.ctx.fillStyle = tank.color;
        this.ctx.fillRect(-tank.size / 2 + 2, -tank.size / 2 + 2, tank.size - 4, tank.size - 4);
        
        this.ctx.fillStyle = '#333';
        this.ctx.fillRect(-tank.size / 2, -tank.size / 2, 4, tank.size);
        this.ctx.fillRect(tank.size / 2 - 4, -tank.size / 2, 4, tank.size);
        
        this.ctx.fillStyle = '#222';
        for (let i = 0; i < 4; i++) {
            this.ctx.fillRect(-tank.size / 2, -tank.size / 2 + 4 + i * 8, 4, 4);
            this.ctx.fillRect(tank.size / 2 - 4, -tank.size / 2 + 4 + i * 8, 4, 4);
        }
        
        this.ctx.fillStyle = tank.color;
        this.ctx.beginPath();
        this.ctx.arc(0, 0, tank.size / 4, 0, Math.PI * 2);
        this.ctx.fill();
        
        this.ctx.fillStyle = '#222';
        this.ctx.beginPath();
        this.ctx.arc(0, 0, tank.size / 6, 0, Math.PI * 2);
        this.ctx.fill();
        
        this.ctx.fillStyle = '#222';
        this.ctx.fillRect(-3, -tank.size / 2, 6, tank.size / 3);
        
        this.ctx.fillStyle = '#444';
        this.ctx.fillRect(-2, -tank.size / 2 - 4, 4, 4);
        
        if (!tank.isPlayer && tank.type === ENEMY_TYPE.ARMORED && tank.hp > 1) {
            this.ctx.fillStyle = `rgba(255, 255, 0, ${tank.hp / tank.maxHp})`;
            this.ctx.fillRect(-tank.size / 4, -tank.size / 4, tank.size / 2, tank.size / 2);
        }
        
        if (!tank.isPlayer && tank.type === ENEMY_TYPE.BONUS) {
            const flash = Math.sin(Date.now() / 80) > 0;
            if (flash) {
                this.ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
                this.ctx.fillRect(-tank.size / 2, -tank.size / 2, tank.size, tank.size);
            }
        }
        
        this.ctx.restore();
    }
    
    drawBullet(bullet) {
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.3)';
        this.ctx.beginPath();
        this.ctx.arc(bullet.x - bullet.dx * 2, bullet.y - bullet.dy * 2, bullet.size / 3, 0, Math.PI * 2);
        this.ctx.fill();
        
        this.ctx.fillStyle = COLORS.BULLET;
        this.ctx.beginPath();
        this.ctx.arc(bullet.x, bullet.y, bullet.size / 2, 0, Math.PI * 2);
        this.ctx.fill();
        
        this.ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
        this.ctx.beginPath();
        this.ctx.arc(bullet.x, bullet.y, bullet.size / 2 + 2, 0, Math.PI * 2);
        this.ctx.fill();
    }
    
    drawExplosions() {
        this.explosions.forEach(exp => {
            const progress = exp.frame / exp.maxFrames;
            const alpha = 1 - progress;
            const size = exp.size * (1 + progress * 0.5);
            
            this.ctx.globalAlpha = alpha;
            
            this.ctx.fillStyle = '#ff6600';
            this.ctx.beginPath();
            this.ctx.arc(exp.x, exp.y, size / 2, 0, Math.PI * 2);
            this.ctx.fill();
            
            this.ctx.fillStyle = '#ffcc00';
            this.ctx.beginPath();
            this.ctx.arc(exp.x, exp.y, size / 3, 0, Math.PI * 2);
            this.ctx.fill();
            
            this.ctx.fillStyle = '#fff';
            this.ctx.beginPath();
            this.ctx.arc(exp.x, exp.y, size / 6, 0, Math.PI * 2);
            this.ctx.fill();
            
            for (let i = 0; i < 8; i++) {
                const angle = (i / 8) * Math.PI * 2 + progress;
                const dist = size / 2 * progress;
                const px = exp.x + Math.cos(angle) * dist;
                const py = exp.y + Math.sin(angle) * dist;
                
                this.ctx.fillStyle = '#ff6600';
                this.ctx.beginPath();
                this.ctx.arc(px, py, 3 * (1 - progress), 0, Math.PI * 2);
                this.ctx.fill();
            }
            
            this.ctx.globalAlpha = 1.0;
        });
    }
    
    gameLoop() {
        if (this.state === 'playing') {
            this.handleInput();
            this.updateEnemies();
            this.updateBullets();
            this.updatePowerups();
            this.updatePowerupSpawn();
            this.updateExplosions();
        }
        
        this.draw();
        
        requestAnimationFrame(() => this.gameLoop());
    }
}

class Tank {
    constructor(x, y, direction, color, isPlayer, type = ENEMY_TYPE.NORMAL) {
        this.x = x;
        this.y = y;
        this.direction = direction;
        this.color = color;
        this.isPlayer = isPlayer;
        this.type = type;
        this.size = TILE_SIZE - 4;
        
        this.level = 1;
        this.maxLevel = 4;
        
        this.hp = 1;
        this.maxHp = 1;
        
        this.invincible = false;
        
        this.spawning = false;
        this.spawnTimer = 0;
        this.spawnDuration = 1000;
        
        this.aiTimer = 0;
        this.aiChangeInterval = 60 + Math.random() * 60;
        
        this.iceSlideDx = 0;
        this.iceSlideDy = 0;
        
        this.lastShotTime = 0;
        
        this.updateStats();
    }
    
    updateStats() {
        if (this.isPlayer) {
            switch (this.level) {
                case 1:
                    this.speed = 2;
                    this.bulletCount = 1;
                    this.bulletSpeed = 4;
                    this.canDestroySteel = false;
                    this.shootCooldown = 400;
                    break;
                case 2:
                    this.speed = 2.5;
                    this.bulletCount = 1;
                    this.bulletSpeed = 5;
                    this.canDestroySteel = false;
                    this.shootCooldown = 350;
                    break;
                case 3:
                    this.speed = 2.5;
                    this.bulletCount = 2;
                    this.bulletSpeed = 5;
                    this.canDestroySteel = false;
                    this.shootCooldown = 300;
                    break;
                case 4:
                    this.speed = 3;
                    this.bulletCount = 2;
                    this.bulletSpeed = 6;
                    this.canDestroySteel = true;
                    this.shootCooldown = 250;
                    break;
            }
            
            const colors = [COLORS.PLAYER, COLORS.PLAYER_LEVEL2, COLORS.PLAYER_LEVEL3, COLORS.PLAYER_LEVEL4];
            this.color = colors[this.level - 1];
        } else {
            if (this.bulletCount === undefined) {
                this.bulletCount = 1;
                this.bulletSpeed = 4;
                this.canDestroySteel = false;
                this.shootCooldown = 1500;
                this.lastShotTime = 0;
            }
        }
    }
    
    levelUp() {
        if (this.level < this.maxLevel) {
            this.level++;
            this.updateStats();
            return true;
        }
        return false;
    }
    
    shoot() {
        const now = Date.now();
        if (now - this.lastShotTime > this.shootCooldown) {
            this.lastShotTime = now;
            return true;
        }
        return false;
    }
    
    createBullets() {
        const bullets = [];
        const now = Date.now();
        
        for (let i = 0; i < this.bulletCount; i++) {
            let bx = this.x + this.size / 2;
            let by = this.y + this.size / 2;
            let bdx = 0;
            let bdy = 0;
            
            switch (this.direction) {
                case DIRECTION.UP:
                    by = this.y;
                    bdy = -this.bulletSpeed;
                    bx += (i - (this.bulletCount - 1) / 2) * 4;
                    break;
                case DIRECTION.DOWN:
                    by = this.y + this.size;
                    bdy = this.bulletSpeed;
                    bx += (i - (this.bulletCount - 1) / 2) * 4;
                    break;
                case DIRECTION.LEFT:
                    bx = this.x;
                    bdx = -this.bulletSpeed;
                    by += (i - (this.bulletCount - 1) / 2) * 4;
                    break;
                case DIRECTION.RIGHT:
                    bx = this.x + this.size;
                    bdx = this.bulletSpeed;
                    by += (i - (this.bulletCount - 1) / 2) * 4;
                    break;
            }
            
            bullets.push(new Bullet(bx, by, bdx, bdy, this.isPlayer, this.canDestroySteel));
        }
        
        this.lastShotTime = now;
        return bullets;
    }
    
    updateAI() {
        if (this.isPlayer) return;
        
        this.aiTimer++;
        if (this.aiTimer >= this.aiChangeInterval) {
            this.aiTimer = 0;
            this.aiChangeInterval = 60 + Math.random() * 60;
            
            if (Math.random() < 0.3) {
                this.changeDirection();
            }
        }
    }
    
    changeDirection() {
        const directions = [DIRECTION.UP, DIRECTION.DOWN, DIRECTION.LEFT, DIRECTION.RIGHT];
        const currentIndex = directions.indexOf(this.direction);
        directions.splice(currentIndex, 1);
        
        this.direction = directions[Math.floor(Math.random() * directions.length)];
    }
    
    shouldShoot() {
        if (this.isPlayer) return false;
        
        const now = Date.now();
        if (now - this.lastShotTime < this.shootCooldown) {
            return false;
        }
        
        const baseChance = this.type === ENEMY_TYPE.FAST ? 0.03 : 0.02;
        if (Math.random() < baseChance) {
            this.lastShotTime = now;
            return true;
        }
        return false;
    }
}

class Bullet {
    constructor(x, y, dx, dy, isPlayerBullet, canDestroySteel = false) {
        this.x = x;
        this.y = y;
        this.dx = dx;
        this.dy = dy;
        this.isPlayerBullet = isPlayerBullet;
        this.canDestroySteel = canDestroySteel;
        this.size = 6;
    }
    
    update() {
        this.x += this.dx;
        this.y += this.dy;
    }
}

document.addEventListener('DOMContentLoaded', () => {
    new Game();
});
