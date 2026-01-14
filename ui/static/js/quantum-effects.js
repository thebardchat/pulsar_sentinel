/**
 * PULSAR SENTINEL - Quantum Visual Effects
 * Creates animated particle background and quantum visual effects
 */

class QuantumParticles {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) return;

        this.ctx = this.canvas.getContext('2d');
        this.particles = [];
        this.connections = [];
        this.mouse = { x: null, y: null, radius: 150 };

        this.colors = {
            primary: '#00f0ff',
            secondary: '#ff00ff',
            tertiary: '#ffd700'
        };

        this.init();
        this.animate();
        this.bindEvents();
    }

    init() {
        this.resize();
        this.createParticles();
    }

    resize() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    createParticles() {
        const particleCount = Math.floor((this.canvas.width * this.canvas.height) / 15000);
        this.particles = [];

        for (let i = 0; i < particleCount; i++) {
            this.particles.push({
                x: Math.random() * this.canvas.width,
                y: Math.random() * this.canvas.height,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5,
                radius: Math.random() * 2 + 1,
                color: this.getRandomColor(),
                pulse: Math.random() * Math.PI * 2,
                pulseSpeed: Math.random() * 0.02 + 0.01
            });
        }
    }

    getRandomColor() {
        const colors = [this.colors.primary, this.colors.secondary, this.colors.tertiary];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    drawParticle(particle) {
        const pulseScale = 1 + Math.sin(particle.pulse) * 0.3;
        const radius = particle.radius * pulseScale;

        // Glow effect
        const gradient = this.ctx.createRadialGradient(
            particle.x, particle.y, 0,
            particle.x, particle.y, radius * 3
        );
        gradient.addColorStop(0, particle.color);
        gradient.addColorStop(0.5, particle.color + '40');
        gradient.addColorStop(1, 'transparent');

        this.ctx.beginPath();
        this.ctx.arc(particle.x, particle.y, radius * 3, 0, Math.PI * 2);
        this.ctx.fillStyle = gradient;
        this.ctx.fill();

        // Core
        this.ctx.beginPath();
        this.ctx.arc(particle.x, particle.y, radius, 0, Math.PI * 2);
        this.ctx.fillStyle = particle.color;
        this.ctx.fill();
    }

    updateParticle(particle) {
        particle.x += particle.vx;
        particle.y += particle.vy;
        particle.pulse += particle.pulseSpeed;

        // Mouse interaction
        if (this.mouse.x !== null) {
            const dx = this.mouse.x - particle.x;
            const dy = this.mouse.y - particle.y;
            const distance = Math.sqrt(dx * dx + dy * dy);

            if (distance < this.mouse.radius) {
                const force = (this.mouse.radius - distance) / this.mouse.radius;
                particle.vx -= (dx / distance) * force * 0.02;
                particle.vy -= (dy / distance) * force * 0.02;
            }
        }

        // Boundary check
        if (particle.x < 0 || particle.x > this.canvas.width) particle.vx *= -1;
        if (particle.y < 0 || particle.y > this.canvas.height) particle.vy *= -1;

        // Velocity dampening
        particle.vx *= 0.999;
        particle.vy *= 0.999;

        // Minimum velocity
        if (Math.abs(particle.vx) < 0.1) particle.vx = (Math.random() - 0.5) * 0.5;
        if (Math.abs(particle.vy) < 0.1) particle.vy = (Math.random() - 0.5) * 0.5;
    }

    drawConnections() {
        const maxDistance = 150;

        for (let i = 0; i < this.particles.length; i++) {
            for (let j = i + 1; j < this.particles.length; j++) {
                const dx = this.particles[i].x - this.particles[j].x;
                const dy = this.particles[i].y - this.particles[j].y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                if (distance < maxDistance) {
                    const opacity = (1 - distance / maxDistance) * 0.3;

                    this.ctx.beginPath();
                    this.ctx.moveTo(this.particles[i].x, this.particles[i].y);
                    this.ctx.lineTo(this.particles[j].x, this.particles[j].y);
                    this.ctx.strokeStyle = `rgba(0, 240, 255, ${opacity})`;
                    this.ctx.lineWidth = 0.5;
                    this.ctx.stroke();
                }
            }
        }
    }

    animate() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Draw connections first (behind particles)
        this.drawConnections();

        // Update and draw particles
        for (const particle of this.particles) {
            this.updateParticle(particle);
            this.drawParticle(particle);
        }

        requestAnimationFrame(() => this.animate());
    }

    bindEvents() {
        window.addEventListener('resize', () => {
            this.resize();
            this.createParticles();
        });

        window.addEventListener('mousemove', (e) => {
            this.mouse.x = e.clientX;
            this.mouse.y = e.clientY;
        });

        window.addEventListener('mouseout', () => {
            this.mouse.x = null;
            this.mouse.y = null;
        });
    }
}

// Glitch Effect for Text
class GlitchText {
    constructor(element) {
        this.element = element;
        this.originalText = element.textContent;
        this.glitchChars = '!@#$%^&*()_+-=[]{}|;:,.<>?/~`';
        this.isGlitching = false;

        this.init();
    }

    init() {
        this.element.addEventListener('mouseenter', () => this.startGlitch());
        this.element.addEventListener('mouseleave', () => this.stopGlitch());
    }

    startGlitch() {
        if (this.isGlitching) return;
        this.isGlitching = true;
        this.glitch();
    }

    stopGlitch() {
        this.isGlitching = false;
        this.element.textContent = this.originalText;
    }

    glitch() {
        if (!this.isGlitching) return;

        let glitchedText = '';
        for (let i = 0; i < this.originalText.length; i++) {
            if (Math.random() < 0.1) {
                glitchedText += this.glitchChars[Math.floor(Math.random() * this.glitchChars.length)];
            } else {
                glitchedText += this.originalText[i];
            }
        }

        this.element.textContent = glitchedText;

        setTimeout(() => {
            this.element.textContent = this.originalText;
            setTimeout(() => this.glitch(), 50 + Math.random() * 100);
        }, 50);
    }
}

// Typing Effect
class TypeWriter {
    constructor(element, texts, speed = 100) {
        this.element = element;
        this.texts = texts;
        this.speed = speed;
        this.textIndex = 0;
        this.charIndex = 0;
        this.isDeleting = false;

        this.type();
    }

    type() {
        const currentText = this.texts[this.textIndex];

        if (this.isDeleting) {
            this.element.textContent = currentText.substring(0, this.charIndex - 1);
            this.charIndex--;
        } else {
            this.element.textContent = currentText.substring(0, this.charIndex + 1);
            this.charIndex++;
        }

        let typeSpeed = this.speed;

        if (this.isDeleting) {
            typeSpeed /= 2;
        }

        if (!this.isDeleting && this.charIndex === currentText.length) {
            typeSpeed = 2000;
            this.isDeleting = true;
        } else if (this.isDeleting && this.charIndex === 0) {
            this.isDeleting = false;
            this.textIndex = (this.textIndex + 1) % this.texts.length;
            typeSpeed = 500;
        }

        setTimeout(() => this.type(), typeSpeed);
    }
}

// Counter Animation
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;

    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }

        if (target >= 1000000) {
            element.textContent = (current / 1000000).toFixed(1) + 'M';
        } else if (target >= 1000) {
            element.textContent = (current / 1000).toFixed(1) + 'K';
        } else {
            element.textContent = Math.floor(current).toLocaleString();
        }
    }, 16);
}

// Initialize effects on page load
document.addEventListener('DOMContentLoaded', () => {
    // Initialize quantum particles
    new QuantumParticles('quantum-particles');

    // Initialize glitch effects on elements with .glitch class
    document.querySelectorAll('.glitch').forEach(el => new GlitchText(el));

    // Initialize counters with data-count attribute
    document.querySelectorAll('[data-count]').forEach(el => {
        const target = parseInt(el.dataset.count);
        animateCounter(el, target);
    });

    // Add smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });
});

// Export for use in other scripts
window.QuantumEffects = {
    QuantumParticles,
    GlitchText,
    TypeWriter,
    animateCounter
};
