// Initialize Lucide icons
document.addEventListener('DOMContentLoaded', function() {
    lucide.createIcons();
    
    // Initialize tabs functionality
    initializeTabs();
});

// Download functionality
function handleDownload(platform) {
    switch (platform) {
        case 'windows':
            // For Windows executable download - point to actual file location
            const windowsUrl = 'landing_page/downloads/digital-wellness-tracker-windows.exe.lnk';
            // Try to download, if fails, show message
            downloadFile(windowsUrl, 'digital-wellness-tracker-windows.exe');
            break;

        case 'mac':
            // For macOS app download
            showNotification('macOS version coming soon!', 'info');
            break;

        case 'linux':
            // For Linux AppImage download
            showNotification('Linux version coming soon!', 'info');
            break;

        case 'source':
            // Redirect to GitHub repository
            window.open('https://github.com/DivyanshM30/digital_wellness', '_blank');
            break;
    }
}

function downloadFile(url, filename) {
    // Check if file exists first
    fetch(url, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                // Create a temporary link element
                const link = document.createElement('a');
                link.href = url;
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                showNotification(`Downloading ${filename}...`);
            } else {
                showNotification('Download file not found. Please check the repository for the latest release.', 'info');
            }
        })
        .catch(() => {
            // If file doesn't exist, redirect to GitHub releases
            showNotification('Redirecting to GitHub for download...', 'info');
            setTimeout(() => {
                window.open('https://github.com/DivyanshM30/digital_wellness/releases', '_blank');
            }, 1000);
        });
}

function showNotification(message, type = 'success') {
    // Create notification element
    const notification = document.createElement('div');
    const bgColor = type === 'info' ? '#f59e0b' : '#10b981';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${bgColor};
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 0.75rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.2);
        z-index: 1000;
        animation: slideIn 0.3s ease;
        font-weight: 500;
        max-width: 300px;
    `;
    notification.textContent = message;
    
    // Add animation keyframes
    if (!document.querySelector('#notification-styles')) {
        const style = document.createElement('style');
        style.id = 'notification-styles';
        style.textContent = `
            @keyframes slideIn {
                from { transform: translateX(100%); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }
            @keyframes slideOut {
                from { transform: translateX(0); opacity: 1; }
                to { transform: translateX(100%); opacity: 0; }
            }
        `;
        document.head.appendChild(style);
    }
    
    document.body.appendChild(notification);
    
    // Remove notification after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Tabs functionality
function initializeTabs() {
    const tabTriggers = document.querySelectorAll('.tab-trigger');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabTriggers.forEach(trigger => {
        trigger.addEventListener('click', () => {
            const targetTab = trigger.getAttribute('data-tab');
            
            // Remove active class from all triggers and contents
            tabTriggers.forEach(t => t.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            // Add active class to clicked trigger and corresponding content
            trigger.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });
}

// Smooth scrolling for anchor links
document.addEventListener('click', function(e) {
    if (e.target.tagName === 'A' && e.target.getAttribute('href').startsWith('#')) {
        e.preventDefault();
        const targetId = e.target.getAttribute('href').substring(1);
        const targetElement = document.getElementById(targetId);
        
        if (targetElement) {
            targetElement.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    }
});

// Add scroll animations
function addScrollAnimations() {
    const observerOptions = {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    };
    
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    }, observerOptions);
    
    // Observe elements for animation
    const animatedElements = document.querySelectorAll('.feature-card, .architecture-card, .implementation-card');
    animatedElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(20px)';
        el.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
        observer.observe(el);
    });
}

// Initialize scroll animations when page loads
document.addEventListener('DOMContentLoaded', addScrollAnimations);

// Add loading state to buttons
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('btn') && !e.target.classList.contains('tab-trigger')) {
        const originalText = e.target.innerHTML;
        e.target.innerHTML = '<i data-lucide="loader-2"></i> Loading...';
        e.target.disabled = true;
        
        // Re-initialize icons for the new loader icon
        lucide.createIcons();
        
        // Reset button after 2 seconds
        setTimeout(() => {
            e.target.innerHTML = originalText;
            e.target.disabled = false;
            lucide.createIcons();
        }, 2000);
    }
});

// Add parallax effect to hero section
window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    const heroSection = document.querySelector('.hero-section');
    
    if (heroSection) {
        const rate = scrolled * -0.5;
        heroSection.style.transform = `translateY(${rate}px)`;
    }
});

// Add typing effect to hero title (optional enhancement)
function addTypingEffect() {
    const heroTitle = document.querySelector('.hero-text h1');
    if (heroTitle) {
        const text = heroTitle.textContent;
        heroTitle.textContent = '';
        
        let i = 0;
        const typeWriter = () => {
            if (i < text.length) {
                heroTitle.textContent += text.charAt(i);
                i++;
                setTimeout(typeWriter, 50);
            }
        };
        
        // Start typing effect after a short delay
        setTimeout(typeWriter, 500);
    }
}

// Uncomment the line below if you want the typing effect
document.addEventListener('DOMContentLoaded', addTypingEffect);