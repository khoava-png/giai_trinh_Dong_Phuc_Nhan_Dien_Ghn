/* ┌────────────────────────────────────────────────────────────┐
   │  CDDV EForm Portal v7.0 — JavaScript                       │
   │  GSAP ScrollTrigger + Interactive Confirm Modal            │
   │  Delivery Edition                                          │
   └────────────────────────────────────────────────────────────┘ */

document.addEventListener('DOMContentLoaded', () => {
  gsap.registerPlugin(ScrollTrigger);

  // ═══ NAV: scrolled state ═══
  const nav = document.getElementById('navFloat');
  const navInner = nav.querySelector('.nav-inner');

  window.addEventListener('scroll', () => {
    navInner.classList.toggle('scrolled', window.scrollY > 20);
  });

  // ═══ HERO: staggered reveal ═══
  const heroReveals = document.querySelectorAll('.hero [data-reveal]');
  if (heroReveals.length) {
    gsap.fromTo(heroReveals,
      { opacity: 0, y: 28 },
      {
        opacity: 1, y: 0,
        duration: 0.7,
        stagger: 0.12,
        ease: 'power3.out',
        delay: 0.2
      }
    );
  }

  /* ═══════════════════════════════════════════════════════════
   04. SCROLL REVEAL
   ═══════════════════════════════════════════════════════════ */
  const revealEls = document.querySelectorAll('[data-reveal]');
  revealEls.forEach(el => {
    // Skip if already animated in hero or inside timelines
    if (el.closest('.hero')) return;

    ScrollTrigger.create({
      trigger: el,
      start: 'top 85%',
      onEnter: () => {
        gsap.to(el, {
          opacity: 1,
          y: 0,
          duration: 0.65,
          ease: 'power3.out'
        });
      },
      once: true
    });
  });

  // ═══ CARD HOVER: subtle lift ═══
  const cards = document.querySelectorAll('.bento-card, .fix-card, .tm-compare-card, .gallery-item');
  cards.forEach(card => {
    card.addEventListener('mouseenter', () => {
      gsap.to(card, {
        y: -3,
        duration: 0.3,
        ease: 'power2.out'
      });
    });
    card.addEventListener('mouseleave', () => {
      gsap.to(card, {
        y: 0,
        duration: 0.4,
        ease: 'power2.out'
      });
    });
  });

  // ═══ STAT COUNTER: animate numbers on scroll ═══
  const statNums = document.querySelectorAll('.hero-stat-num');
  statNums.forEach(stat => {
    ScrollTrigger.create({
      trigger: stat,
      start: 'top 90%',
      onEnter: () => {
        gsap.fromTo(stat,
          { scale: 0.8, opacity: 0 },
          { scale: 1, opacity: 1, duration: 0.5, ease: 'back.out(1.7)' }
        );
      },
      once: true
    });
  });

  // ═══ FLOW STEPS: stagger reveal ═══
  const flowSteps = document.querySelectorAll('.flow-step');
  flowSteps.forEach((step, i) => {
    ScrollTrigger.create({
      trigger: step,
      start: 'top 80%',
      onEnter: () => {
        gsap.fromTo(step.querySelector('.flow-step-card'),
          { opacity: 0, y: 24, scale: 0.97 },
          { opacity: 1, y: 0, scale: 1, duration: 0.5, delay: i * 0.1, ease: 'power3.out' }
        );
      },
      once: true
    });
  });

  // ═══ PARALLAX: section backgrounds ═══
  const bgSections = document.querySelectorAll('.section--bg');
  bgSections.forEach(section => {
    ScrollTrigger.create({
      trigger: section,
      start: 'top bottom',
      end: 'bottom top',
      onUpdate: self => {
        const progress = self.progress;
        section.style.backgroundPositionY = `${progress * 15}%`;
      }
    });
  });

  // ═══ SMOOTH SCROLL: nav links ═══
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function(e) {
      const href = this.getAttribute('href');
      // Only do smooth scroll if it doesn't target EForm link
      if (href.startsWith('#')) {
        const target = document.querySelector(href);
        if (target) {
          e.preventDefault();
          target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }
    });
  });

  /* ═══════════════════════════════════════════════════════════
   15. INTERACTIVE CHECKBOX & CONFIRMATION MODAL
   ═══════════════════════════════════════════════════════════ */
  const confirmCheck = document.getElementById('confirmCheck');
  const confirmCard = document.getElementById('confirmCard');
  const eformBtns = document.querySelectorAll('.eform-btn');
  const modalOverlay = document.getElementById('modalOverlay');
  const modalBtnConfirm = document.getElementById('modalBtnConfirm');
  const modalBtnClose = document.getElementById('modalBtnClose');

  let pendingUrl = null;

  // Initialize status from localStorage
  if (confirmCheck && confirmCard) {
    const isConfirmed = localStorage.getItem('cddv_confirmed') === 'true';
    confirmCheck.checked = isConfirmed;
    if (isConfirmed) {
      confirmCard.classList.add('confirmed');
    } else {
      // Tự động hiển thị popup cảnh báo sau 1.5 giây nếu chưa xác nhận đọc hiểu
      setTimeout(() => {
        openModal();
      }, 1500);
    }

    // Toggle confirm state
    confirmCheck.addEventListener('change', () => {
      const checked = confirmCheck.checked;
      localStorage.setItem('cddv_confirmed', checked ? 'true' : 'false');
      confirmCard.classList.toggle('confirmed', checked);
    });
  }

  // Click Interception on EForm buttons
  eformBtns.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const isConfirmed = localStorage.getItem('cddv_confirmed') === 'true';
      if (!isConfirmed) {
        e.preventDefault();
        pendingUrl = btn.getAttribute('href');
        openModal();
      }
    });
  });

  function openModal() {
    if (modalOverlay) {
      modalOverlay.classList.add('active');
      gsap.fromTo(modalOverlay.querySelector('.modal-box'),
        { scale: 0.9, y: 30, opacity: 0 },
        { scale: 1, y: 0, opacity: 1, duration: 0.4, ease: 'back.out(1.5)' }
      );
    }
  }

  function closeModal() {
    if (modalOverlay) {
      gsap.to(modalOverlay.querySelector('.modal-box'), {
        scale: 0.9, y: 20, opacity: 0, duration: 0.25, ease: 'power2.in',
        onComplete: () => {
          modalOverlay.classList.remove('active');
        }
      });
    }
  }

  if (modalBtnClose) {
    modalBtnClose.addEventListener('click', closeModal);
  }

  if (modalBtnConfirm) {
    modalBtnConfirm.addEventListener('click', () => {
      // Set confirmed
      if (confirmCheck) {
        confirmCheck.checked = true;
        localStorage.setItem('cddv_confirmed', 'true');
        if (confirmCard) confirmCard.classList.add('confirmed');
      }
      closeModal();
      if (pendingUrl) {
        setTimeout(() => {
          window.open(pendingUrl, '_blank');
        }, 300);
      }
    });
  }

  if (modalOverlay) {
    modalOverlay.addEventListener('click', (e) => {
      if (e.target === modalOverlay) {
        closeModal();
      }
    });
  }

  /* ═══════════════════════════════════════════════════════════
   16. VIDEO CONFLICT PREVENTION & SCROLL AUTOPLAY
   ═══════════════════════════════════════════════════════════ */
  const videos = document.querySelectorAll('video');
  
  // GHI CHÚ: Tự động phát video khi cuộn đến và tạm dừng khi cuộn ra ngoài khu vực tiêu đề của section
  videos.forEach(video => {
    // Ngăn chặn phát nhiều video cùng lúc
    video.addEventListener('play', () => {
      videos.forEach(otherVideo => {
        if (otherVideo !== video) {
          otherVideo.pause();
        }
      });
    });

    // Tự động phát/tạm dừng dựa trên vị trí cuộn màn hình
    const section = video.closest('.section');
    if (section) {
      ScrollTrigger.create({
        trigger: section,
        start: 'top 50%', // Khi phần đầu section vào giữa màn hình
        end: 'bottom 20%', // Khi phần cuối section cuộn qua
        onEnter: () => {
          // Trình duyệt có thể block autoplay nếu chưa có tương tác từ user
          video.play().catch(err => console.log('Autoplay blocked:', err));
        },
        onLeave: () => {
          video.pause();
        },
        onEnterBack: () => {
          video.play().catch(err => console.log('Autoplay blocked:', err));
        },
        onLeaveBack: () => {
          video.pause();
        }
      });
    }
  });

  console.log('%cCDDV Portal v7.0 %cloaded — Delivery Edition',
    'color: #FF7A00; font-weight: bold;',
    'color: #646464;');
});
