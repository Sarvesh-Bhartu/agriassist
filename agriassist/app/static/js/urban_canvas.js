/**
 * urban_canvas.js
 * Handles the interactive polygon drawing on balcony/terrace images.
 * Theme: Neon Yellow (#CCFF00) for markers and lines.
 */

class UrbanPolygonCanvas {
    constructor(canvasId, inputId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        this.inputId = inputId; // Hidden input to store polygon JSON
        this.points = [];
        this.isClosed = false;
        this.image = new Image();
        this.neoYellow = "#CCFF00";
        
        this.setupEventListeners();
    }

    loadImage(src) {
        this.image.onload = () => {
            this.resizeCanvas();
            this.draw();
        };
        this.image.src = src;
    }

    resizeCanvas() {
        const parent = this.canvas.parentElement;
        const ratio = this.image.width / this.image.height;
        
        // Scale canvas to fit parent width while maintaining image aspect ratio
        this.canvas.width = parent.clientWidth;
        this.canvas.height = parent.clientWidth / ratio;
    }

    setupEventListeners() {
        this.canvas.addEventListener('mousedown', (e) => this.addPoint(e));
        this.canvas.addEventListener('contextmenu', (e) => {
            e.preventDefault();
            this.closePolygon();
        });
        
        window.addEventListener('resize', () => {
            if (this.image.src) {
                this.resizeCanvas();
                this.draw();
            }
        });
    }

    addPoint(e) {
        if (this.isClosed) return;

        const rect = this.canvas.getBoundingClientRect();
        const x = (e.clientX - rect.left) / this.canvas.width;
        const y = (e.clientY - rect.top) / this.canvas.height;
        
        this.points.push({ x, y });
        this.updateInput();
        this.draw();
        
        if (this.points.length >= 8) { // Default cap or auto-close logic if needed
            // Optional: auto-close if too many points
        }
    }

    closePolygon() {
        if (this.points.length < 3) return;
        this.isClosed = true;
        this.updateInput();
        this.draw();
    }

    reset() {
        this.points = [];
        this.isClosed = false;
        this.updateInput();
        this.draw();
    }

    updateInput() {
        const input = document.getElementById(this.inputId);
        if (input) {
            input.value = JSON.stringify(this.points);
        }
    }

    draw() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Draw Image
        this.ctx.drawImage(this.image, 0, 0, this.canvas.width, this.canvas.height);
        
        if (this.points.length === 0) return;

        // Draw Lines
        this.ctx.beginPath();
        this.ctx.strokeStyle = this.neoYellow;
        this.ctx.lineWidth = 3;
        this.ctx.setLineDash([]);
        
        const firstX = this.points[0].x * this.canvas.width;
        const firstY = this.points[0].y * this.canvas.height;
        this.ctx.moveTo(firstX, firstY);

        for (let i = 1; i < this.points.length; i++) {
            const px = this.points[i].x * this.canvas.width;
            const py = this.points[i].y * this.canvas.height;
            this.ctx.lineTo(px, py);
        }

        if (this.isClosed) {
            this.ctx.closePath();
            // Fill with semi-transparent yellow
            this.ctx.fillStyle = "rgba(204, 255, 0, 0.2)";
            this.ctx.fill();
        }
        this.ctx.stroke();

        // Draw Points
        this.points.forEach((p, idx) => {
            const px = p.x * this.canvas.width;
            const py = p.y * this.canvas.height;
            
            this.ctx.fillStyle = (idx === 0) ? "#FFFFFF" : this.neoYellow; // Start point is white
            this.ctx.beginPath();
            this.ctx.arc(px, py, 6, 0, Math.PI * 2);
            this.ctx.fill();
            this.ctx.strokeStyle = "#000000";
            this.ctx.lineWidth = 1;
            this.ctx.stroke();
        });
    }
}
