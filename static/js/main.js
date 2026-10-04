/**
 * College Marketplace — Client-Side JavaScript
 * =============================================
 * Handles: mobile nav toggle, image preview, flash auto-dismiss,
 * navbar scroll effect, and form interactions.
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── Mobile Navigation Toggle ────────────────────────────
    const navToggle = document.getElementById('nav-toggle');
    const navLinks  = document.getElementById('nav-links');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('active');
            navToggle.classList.toggle('active');
        });

        // Close mobile menu when a link is clicked
        navLinks.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                navLinks.classList.remove('active');
                navToggle.classList.remove('active');
            });
        });
    }

    // ── Navbar scroll effect ────────────────────────────────
    const navbar = document.getElementById('main-navbar');
    if (navbar) {
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            const currentScroll = window.scrollY;
            if (currentScroll > 50) {
                navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.3)';
            } else {
                navbar.style.boxShadow = 'none';
            }
            lastScroll = currentScroll;
        }, { passive: true });
    }

    // ── Flash Message Auto-Dismiss ──────────────────────────
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach((msg, index) => {
        setTimeout(() => {
            msg.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            msg.style.opacity = '0';
            msg.style.transform = 'translateX(80px)';
            setTimeout(() => msg.remove(), 500);
        }, 4000 + (index * 500)); // Stagger dismissal
    });

    // ── Image Upload Preview ────────────────────────────────
    const imageInput = document.getElementById('product-image-input');
    const imagePreview = document.getElementById('image-preview');
    const previewImg = document.getElementById('preview-img');
    const uploadLabel = document.getElementById('image-upload-label');

    if (imageInput && imagePreview && previewImg) {
        imageInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                // Validate file size (5MB)
                if (file.size > 5 * 1024 * 1024) {
                    alert('File size must be less than 5MB.');
                    imageInput.value = '';
                    return;
                }

                const reader = new FileReader();
                reader.onload = (ev) => {
                    previewImg.src = ev.target.result;
                    imagePreview.style.display = 'block';
                    if (uploadLabel) {
                        uploadLabel.style.display = 'none';
                    }
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // ── Product Cards Stagger Animation ─────────────────────
    const productCards = document.querySelectorAll('.product-card, .listing-card');
    if (productCards.length > 0) {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0)';
                    }, index * 50);
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.1 });

        productCards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            observer.observe(card);
        });
    }

    // ── Stat Cards Animation ────────────────────────────────
    const statCards = document.querySelectorAll('.stat-card');
    if (statCards.length > 0) {
        const statObserver = new IntersectionObserver((entries) => {
            entries.forEach((entry, index) => {
                if (entry.isIntersecting) {
                    setTimeout(() => {
                        entry.target.style.opacity = '1';
                        entry.target.style.transform = 'translateY(0) scale(1)';
                    }, index * 100);
                    statObserver.unobserve(entry.target);
                }
            });
        }, { threshold: 0.2 });

        statCards.forEach(card => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(15px) scale(0.95)';
            card.style.transition = 'opacity 0.5s ease, transform 0.5s cubic-bezier(0.4, 0, 0.2, 1)';
            statObserver.observe(card);
        });
    }
});

/**
 * Remove image preview and reset file input.
 * Called from the remove button in add/edit product forms.
 */
function removeImagePreview() {
    const imageInput   = document.getElementById('product-image-input');
    const imagePreview = document.getElementById('image-preview');
    const uploadLabel  = document.getElementById('image-upload-label');

    if (imageInput)   imageInput.value = '';
    if (imagePreview)  imagePreview.style.display = 'none';
    if (uploadLabel)   uploadLabel.style.display = 'flex';
}
