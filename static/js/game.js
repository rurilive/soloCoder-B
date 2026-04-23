const TILE_SIZE = 40;
const GRID_SIZE = 13;
const CANVAS_SIZE = TILE_SIZE * GRID_SIZE;

const TILE = {
    EMPTY: 0,
    BRICK: 1,
    STEEL: 2,
    WATER: 3,
    GRASS: 4,
    BASE: 5
};

const DIRECTION = {
    UP: 0,
    RIGHT: 1,
    DOWN: 2,
    LEFT: 3
};

const COLORS = {
    PLAYER: '#4CAF50',
    ENEMY: '#f44336',
    BRICK: '#8B4513',
    STEEL: '#808080',
    WATER: '#1e90ff',
    GRASS: '#228B22',
    BASE: '#ffcc00',
    BULLET: '#fff'
};

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
        
        this.state = 'start';
        this.level = 1;
        this.score = 0;
        this.lives = 3;
        
        this.player = null;
        this.enemies = [];
        this.bullets = [];
        this.map = [];
        this.explosions = [];
        
        this.keys = {};
        this.lastShotTime = 0;
        this.shootCooldown = 300;
        
        this.maxEnemies = 4;
        this.enemiesRemaining = 10;
        this.enemySpawnTimer = 0;
        this.enemySpawnInterval = 3000;
        
        this.init();
    }
    
    init() {
        this.bindEvents();
        this.generateMap();
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
    
    generateMap() {
        this.map = [];
        for (let y = 0; y < GRID_SIZE; y++) {
            this.map[y] = [];
            for (let x = 0; x < GRID_SIZE; x++) {
                this.map[y][x] = TILE.EMPTY;
            }
        }
        
        const baseX = 6;
        const baseY = 12;
        this.map[baseY][baseX] = TILE.BASE;
        
        this.map[baseY - 1][baseX - 1] = TILE.BRICK;
        this.map[baseY - 1][baseX] = TILE.BRICK;
        this.map[baseY - 1][baseX + 1] = TILE.BRICK;
        this.map[baseY][baseX - 1] = TILE.BRICK;
        this.map[baseY][baseX + 1] = TILE.BRICK;
        
        const obstacles = [
            { x: 2, y: 4, type: 'group' },
            { x: 4, y: 4, type: 'group' },
            { x: 8, y: 4, type: 'group' },
            { x: 10, y: 4, type: 'group' },
            { x: 3, y: 8, type: 'steel' },
            { x: 9, y: 8, type: 'steel' },
            { x: 1, y: 6, type: 'water' },
            { x: 11, y: 6, type: 'water' },
            { x: 5, y: 10, type: 'grass' },
            { x: 7, y: 10, type: 'grass' },
        ];
        
        obstacles.forEach(obs => {
            if (obs.type === 'group') {
                for (let dy = 0; dy < 2; dy++) {
                    for (let dx = 0; dx < 2; dx++) {
                        if (this.isValidPosition(obs.x + dx, obs.y + dy)) {
                            this.map[obs.y + dy][obs.x + dx] = TILE.BRICK;
                        }
                    }
                }
            } else if (obs.type === 'steel') {
                for (let dy = 0; dy < 2; dy++) {
                    for (let dx = 0; dx < 2; dx++) {
                        if (this.isValidPosition(obs.x + dx, obs.y + dy)) {
                            this.map[obs.y + dy][obs.x + dx] = TILE.STEEL;
                        }
                    }
                }
            } else if (obs.type === 'water') {
                for (let dy = 0; dy < 3; dy++) {
                    for (let dx = 0; dx < 1; dx++) {
                        if (this.isValidPosition(obs.x + dx, obs.y + dy)) {
                            this.map[obs.y + dy][obs.x + dx] = TILE.WATER;
                        }
                    }
                }
            } else if (obs.type === 'grass') {
                for (let dy = 0; dy < 2; dy++) {
                    for (let dx = 0; dx < 2; dx++) {
                        if (this.isValidPosition(obs.x + dx, obs.y + dy)) {
                            this.map[obs.y + dy][obs.x + dx] = TILE.GRASS;
                        }
                    }
                }
            }
        });
    }
    
    isValidPosition(x, y) {
        return x >= 0 && x < GRID_SIZE && y >= 0 && y < GRID_SIZE && this.map[y][x] === TILE.EMPTY;
    }
    
    spawnPlayer() {
        this.player = new Tank(
            TILE_SIZE * 4,
            CANVAS_SIZE - TILE_SIZE,
            DIRECTION.UP,
            COLORS.PLAYER,
            true
        );
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
        
        if (!blocked) {
            const enemy = new Tank(
                spawn.x,
                spawn.y,
                DIRECTION.DOWN,
                COLORS.ENEMY,
                false
            );
            this.enemies.push(enemy);
            this.enemiesRemaining--;
        }
    }
    
    startGame() {
        this.state = 'playing';
        this.hideOverlay();
        this.enemySpawnTimer = Date.now();
    }
    
    pauseGame() {
        this.state = 'paused';
        this.showOverlay('游戏暂停', '按空格键继续游戏');
    }
    
    resumeGame() {
        this.state = 'playing';
        this.hideOverlay();
    }
    
    gameOver(win = false) {
        this.state = win ? 'win' : 'gameover';
        if (win) {
            this.showOverlay('关卡通过!', '得分: ' + this.score + ' - 按空格键继续');
        } else {
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
    }
    
    handleInput() {
        if (this.state !== 'playing' || !this.player) return;
        
        let moved = false;
        
        if (this.keys['KeyW'] || this.keys['ArrowUp']) {
            this.player.direction = DIRECTION.UP;
            moved = this.tryMoveTank(this.player, 0, -this.player.speed);
        } else if (this.keys['KeyS'] || this.keys['ArrowDown']) {
            this.player.direction = DIRECTION.DOWN;
            moved = this.tryMoveTank(this.player, 0, this.player.speed);
        } else if (this.keys['KeyA'] || this.keys['ArrowLeft']) {
            this.player.direction = DIRECTION.LEFT;
            moved = this.tryMoveTank(this.player, -this.player.speed, 0);
        } else if (this.keys['KeyD'] || this.keys['ArrowRight']) {
            this.player.direction = DIRECTION.RIGHT;
            moved = this.tryMoveTank(this.player, this.player.speed, 0);
        }
        
        const now = Date.now();
        if (this.keys['Space'] && now - this.lastShotTime > this.shootCooldown) {
            if (this.player.shoot()) {
                this.bullets.push(this.player.createBullet());
                this.lastShotTime = now;
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
        if (now - this.enemySpawnTimer > this.enemySpawnInterval) {
            this.spawnEnemy();
            this.enemySpawnTimer = now;
        }
        
        this.enemies.forEach(enemy => {
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
                this.bullets.push(enemy.createBullet());
            }
        });
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
                    return false;
                }
                
                if (tile === TILE.STEEL) {
                    this.createExplosion(bullet.x, bullet.y, false);
                    return false;
                }
                
                if (tile === TILE.BASE) {
                    this.map[gridY][gridX] = TILE.EMPTY;
                    this.createExplosion(bullet.x, bullet.y, true);
                    this.gameOver(false);
                    return false;
                }
            }
            
            if (bullet.isPlayerBullet) {
                for (let i = this.enemies.length - 1; i >= 0; i--) {
                    const enemy = this.enemies[i];
                    if (this.rectsIntersect(
                        bullet.x - bullet.size / 2, bullet.y - bullet.size / 2, bullet.size, bullet.size,
                        enemy.x, enemy.y, enemy.size, enemy.size
                    )) {
                        this.enemies.splice(i, 1);
                        this.score += 100;
                        this.createExplosion(enemy.x + enemy.size / 2, enemy.y + enemy.size / 2, true);
                        this.updateUI();
                        
                        if (this.enemies.length === 0 && this.enemiesRemaining === 0) {
                            this.gameOver(true);
                        }
                        return false;
                    }
                }
            } else {
                if (this.player && this.rectsIntersect(
                    bullet.x - bullet.size / 2, bullet.y - bullet.size / 2, bullet.size, bullet.size,
                    this.player.x, this.player.y, this.player.size, this.player.size
                )) {
                    this.lives--;
                    this.createExplosion(this.player.x + this.player.size / 2, this.player.y + this.player.size / 2, true);
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
        
        if (this.player) {
            this.drawTank(this.player);
        }
        
        this.enemies.forEach(enemy => this.drawTank(enemy));
        
        this.bullets.forEach(bullet => this.drawBullet(bullet));
        
        this.drawExplosions();
        
        this.drawGrassOverlay();
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
        gradient.addColorStop(0, '#aaa');
        gradient.addColorStop(0.5, '#888');
        gradient.addColorStop(1, '#666');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        this.ctx.strokeStyle = '#555';
        this.ctx.lineWidth = 1;
        this.ctx.strokeRect(x + 2, y + 2, TILE_SIZE - 4, TILE_SIZE - 4);
    }
    
    drawWater(x, y) {
        const gradient = this.ctx.createLinearGradient(x, y, x, y + TILE_SIZE);
        gradient.addColorStop(0, '#4169e1');
        gradient.addColorStop(1, '#1e90ff');
        
        this.ctx.fillStyle = gradient;
        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.3)';
        this.ctx.lineWidth = 1;
        
        for (let i = 0; i < 3; i++) {
            this.ctx.beginPath();
            this.ctx.arc(x + TILE_SIZE / 4 + i * 15, y + TILE_SIZE / 2, 5, 0, Math.PI * 2);
            this.ctx.stroke();
        }
    }
    
    drawGrass(x, y) {
        this.ctx.fillStyle = COLORS.GRASS;
        this.ctx.fillRect(x, y, TILE_SIZE, TILE_SIZE);
        
        this.ctx.fillStyle = '#1a5c1a';
        for (let i = 0; i < 5; i++) {
            const gx = x + Math.random() * TILE_SIZE;
            const gy = y + Math.random() * TILE_SIZE;
            this.ctx.fillRect(gx, gy, 2, 6);
        }
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
    
    drawTank(tank) {
        this.ctx.save();
        this.ctx.translate(tank.x + tank.size / 2, tank.y + tank.size / 2);
        
        const angle = tank.direction * Math.PI / 2;
        this.ctx.rotate(angle);
        
        this.ctx.fillStyle = tank.color;
        this.ctx.fillRect(-tank.size / 2 + 2, -tank.size / 2 + 2, tank.size - 4, tank.size - 4);
        
        this.ctx.fillStyle = '#333';
        this.ctx.fillRect(-tank.size / 2, -tank.size / 2, 4, tank.size);
        this.ctx.fillRect(tank.size / 2 - 4, -tank.size / 2, 4, tank.size);
        
        this.ctx.fillStyle = tank.color;
        this.ctx.beginPath();
        this.ctx.arc(0, 0, tank.size / 4, 0, Math.PI * 2);
        this.ctx.fill();
        
        this.ctx.fillStyle = '#222';
        this.ctx.fillRect(-3, -tank.size / 2, 6, tank.size / 3);
        
        this.ctx.restore();
    }
    
    drawBullet(bullet) {
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
            const size = exp.size * (1 + progress);
            
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
            
            this.ctx.globalAlpha = 1.0;
        });
    }
    
    gameLoop() {
        this.handleInput();
        this.updateEnemies();
        this.updateBullets();
        this.updateExplosions();
        this.draw();
        
        requestAnimationFrame(() => this.gameLoop());
    }
}

class Tank {
    constructor(x, y, direction, color, isPlayer) {
        this.x = x;
        this.y = y;
        this.direction = direction;
        this.color = color;
        this.isPlayer = isPlayer;
        this.size = TILE_SIZE - 4;
        this.speed = isPlayer ? 2 : 1;
        this.lastShotTime = 0;
        this.shootCooldown = isPlayer ? 300 : 1000 + Math.random() * 1000;
        this.aiTimer = 0;
        this.aiChangeInterval = 60 + Math.random() * 60;
    }
    
    shoot() {
        const now = Date.now();
        if (now - this.lastShotTime > this.shootCooldown) {
            this.lastShotTime = now;
            return true;
        }
        return false;
    }
    
    createBullet() {
        let bx = this.x + this.size / 2;
        let by = this.y + this.size / 2;
        let bdx = 0;
        let bdy = 0;
        
        const speed = 4;
        
        switch (this.direction) {
            case DIRECTION.UP:
                by = this.y;
                bdy = -speed;
                break;
            case DIRECTION.DOWN:
                by = this.y + this.size;
                bdy = speed;
                break;
            case DIRECTION.LEFT:
                bx = this.x;
                bdx = -speed;
                break;
            case DIRECTION.RIGHT:
                bx = this.x + this.size;
                bdx = speed;
                break;
        }
        
        return new Bullet(bx, by, bdx, bdy, this.isPlayer);
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
        return Math.random() < 0.02;
    }
}

class Bullet {
    constructor(x, y, dx, dy, isPlayerBullet) {
        this.x = x;
        this.y = y;
        this.dx = dx;
        this.dy = dy;
        this.isPlayerBullet = isPlayerBullet;
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
