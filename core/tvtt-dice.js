// ═══════════════════════════════════════════════════════════════
//  tvtt-dice.js — Animação física de dados para Tartantis VTT
//
//  Todos os tipos de dado (d4, d6, d8, d10, d12, d20, d100)
//  recebem a mesma animação: arremesso, arco, quique e brilho.
//  O d6 usa cubo 3D com faces e pontos. Os demais usam a forma
//  geométrica característica de cada dado em perspectiva 2D.
//
//  API:  DiceAnimator.roll(rolls, sides, author, onSettledCallback)
// ═══════════════════════════════════════════════════════════════

(function () {
  'use strict';

  var SIZE     = 80;   // px — tamanho base do dado
  var HALF     = SIZE / 2;
  var T_FLY    = 1900; // ms — duração do arremesso + pouso
  var T_SHOW   = 1400; // ms — tempo exibindo resultado após pousar
  var T_FADE   = 500;  // ms — fade-out final

  // ── Pontos por face (d6) ──
  var DOTS = {
    1: [[50,50]],
    2: [[72,28],[28,72]],
    3: [[72,28],[50,50],[28,72]],
    4: [[28,28],[72,28],[28,72],[72,72]],
    5: [[28,28],[72,28],[50,50],[28,72],[72,72]],
    6: [[28,24],[72,24],[28,50],[72,50],[28,76],[72,76]]
  };

  // ── Rotação final para cada face de d6 ──
  var FACE_ROT = {
    1: [  0,   0],
    2: [  0, -90],
    3: [ 90,   0],
    4: [-90,   0],
    5: [  0,  90],
    6: [  0, 180]
  };

  // ── Formas geométricas (clip-path) por tipo de dado ──
  var DIE_CLIP = {
    4:   'polygon(50% 2%, 1%  97%, 99% 97%)',                           // triângulo ▲
    8:   'polygon(50% 1%, 99% 50%, 50% 99%, 1%  50%)',                  // losango ◆
    10:  'polygon(50% 1%, 97% 33%, 79% 97%, 21% 97%, 3%  33%)',         // pentágono ⬠
    12:  'polygon(27% 0%, 73% 0%, 100% 50%, 73% 100%, 27% 100%, 0% 50%)', // hexágono ⬡
    20:  'polygon(50% 1%, 3%  92%, 97% 92%)',                           // triângulo d20
    100: null                                                            // círculo ○
  };

  // ── Escala visual de cada tipo (compensar formas menores) ──
  var DIE_SCALE = { 4: 1.15, 8: 1.05, 10: 1.0, 12: 1.0, 20: 1.15, 100: 1.0 };

  // ── Rótulos dos dados ──
  var DIE_LABEL = { 4:'d4', 8:'d8', 10:'d10', 12:'d12', 20:'d20', 100:'d%' };

  // ─────────────────────────────────────────────────────────────
  //  CSS base — injetado uma vez
  // ─────────────────────────────────────────────────────────────
  var style = document.createElement('style');
  style.textContent = [
    // Overlay transparente, sem fundo
    '#tvtt-dice-overlay{',
      'position:fixed;top:0;left:0;right:0;bottom:0;',
      'z-index:9800;pointer-events:none;}',

    // Mover: posição absoluta na tela
    '.mb-mv{position:absolute;will-change:transform;}',

    // Perspectiva aplicada no container de cada dado
    '.mb-persp{',
      'perspective:450px;',
      'position:relative;',
      'width:' + SIZE + 'px;height:' + SIZE + 'px;}',

    // ── Cubo 3D (d6) ──
    '.mb-cube{',
      'width:' + SIZE + 'px;height:' + SIZE + 'px;',
      'position:relative;transform-style:preserve-3d;',
      'will-change:transform;}',

    // Faces do cubo d6
    '.mb-face{',
      'position:absolute;',
      'width:' + SIZE + 'px;height:' + SIZE + 'px;',
      'background:var(--dice-bg-1);',
      'border-radius:13px;',
      'border:2px solid var(--dice-border);',
      'box-shadow:var(--dice-shadow);}',
    '.mb-face::after{content:"";position:absolute;inset:0;border-radius:11px;',
      'background:var(--dice-light);}',

    // Posição das faces no cubo
    '.mb-f1{transform:translateZ('  + HALF + 'px);}',
    '.mb-f2{transform:rotateY( 90deg) translateZ(' + HALF + 'px);}',
    '.mb-f3{transform:rotateX(-90deg) translateZ(' + HALF + 'px);}',
    '.mb-f4{transform:rotateX( 90deg) translateZ(' + HALF + 'px);}',
    '.mb-f5{transform:rotateY(-90deg) translateZ(' + HALF + 'px);}',
    '.mb-f6{transform:rotateY(180deg) translateZ(' + HALF + 'px);}',

    // Pontos do d6
    '.mb-dot{',
      'position:absolute;width:14px;height:14px;',
      'background:radial-gradient(circle at 38% 32%,var(--dice-dot-color),var(--dice-dot-inner));',
      'border-radius:50%;transform:translate(-50%,-50%);',
      'box-shadow:0 1px 2px rgba(0,0,0,.4);}',

    // ── Dado genérico (non-d6) ──
    '.mb-die{',
      'width:' + SIZE + 'px;height:' + SIZE + 'px;',
      'position:relative;',
      'background:var(--dice-bg-2);',
      'box-shadow:var(--dice-shadow-2);',
      'display:flex;align-items:center;justify-content:center;',
      'overflow:hidden;}',

    // Número no dado genérico
    '.mb-die-num{',
      'font-family:"Cinzel Decorative",cursive;',
      'font-size:1.65rem;font-weight:700;line-height:1;',
      'color:var(--dice-num-color);',
      'transition:color .35s,text-shadow .35s;',
      'position:relative;z-index:2;',
      'user-select:none;}',
    '.mb-mv.mb-settle .mb-die-num{',
      'color:var(--dice-num-settled);',
      'text-shadow:var(--dice-num-shadow);}',

    // Rótulo do tipo (d8, d20…) — canto inferior direito
    '.mb-die-label{',
      'position:absolute;bottom:7%;right:9%;',
      'font-family:"Cinzel",serif;',
      'font-size:0.42rem;font-weight:700;letter-spacing:.1em;',
      'color:var(--dice-label-color);',
      'z-index:2;user-select:none;}',

    // Borda interna (imitando chanfro da aresta do dado)
    '.mb-die::before{',
      'content:"";position:absolute;inset:4px;z-index:1;',
      'border:1.5px solid var(--dice-inner-border);',
      'pointer-events:none;}',

    // Reflexo de luz
    '.mb-die::after{',
      'content:"";position:absolute;inset:0;',
      'background:var(--dice-light);',
      'pointer-events:none;z-index:3;}',

    // Sombra no chão
    '.mb-shadow{',
      'position:absolute;',
      'width:' + SIZE + 'px;height:12px;',
      'background:radial-gradient(ellipse,rgba(0,0,0,.45) 0%,transparent 72%);',
      'border-radius:50%;',
      'bottom:-14px;left:0;',
      'transform:scaleX(1.3);',
      'opacity:0;transition:opacity .25s;}',
    '.mb-mv.mb-land .mb-shadow{opacity:1;}',

    // Brilho ao pousar (compartilhado entre d6 e não-d6)
    '.mb-glow{',
      'position:absolute;inset:-6px;',
      'border:2px solid transparent;pointer-events:none;',
      'transition:border-color .4s,box-shadow .45s;}',
    '.mb-mv.mb-settle .mb-glow{',
      'border-color:var(--dice-glow);',
      'box-shadow:var(--dice-glow-shadow);}',

    // border-radius do brilho varia por tipo
    '.mb-glow-sq  {border-radius:15px;}',  // d6: quadrado
    '.mb-glow-tri {border-radius:8px;}',   // d4, d20: triângulo
    '.mb-glow-dia {border-radius:8px;}',   // d8: losango
    '.mb-glow-pent{border-radius:8px;}',   // d10, d12: pentágono/hexágono
    '.mb-glow-circ{border-radius:50%;}'    // d100: círculo
  ].join('');
  document.head.appendChild(style);

  // ─────────────────────────────────────────────────────────────
  //  Overlay
  // ─────────────────────────────────────────────────────────────
  var overlay = document.createElement('div');
  overlay.id = 'tvtt-dice-overlay';
  document.body.appendChild(overlay);

  // ─────────────────────────────────────────────────────────────
  //  Utilitários
  // ─────────────────────────────────────────────────────────────
  function r(min, max) { return min + Math.random() * (max - min); }
  function uid() { return Math.random().toString(36).substr(2, 8); }

  function injectKF(css) {
    var s = document.createElement('style');
    s.textContent = css;
    document.head.appendChild(s);
    return s;
  }

  // Constrói face numerada do d6
  function buildFace(n) {
    var face = document.createElement('div');
    face.className = 'mb-face mb-f' + n;
    (DOTS[n] || []).forEach(function(p) {
      var dot = document.createElement('div');
      dot.className = 'mb-dot';
      dot.style.left = p[0] + '%';
      dot.style.top  = p[1] + '%';
      face.appendChild(dot);
    });
    return face;
  }

  // Constrói elemento visual para dado não-d6
  function buildDieEl(sides, value) {
    var clip  = DIE_CLIP[sides] || null;
    var sc    = DIE_SCALE[sides] || 1.0;
    var label = DIE_LABEL[sides] || ('d' + sides);

    var die = document.createElement('div');
    die.className = 'mb-die';

    // Forma geométrica via clip-path
    if (clip) {
      die.style.clipPath = clip;
      die.style.webkitClipPath = clip;
    } else {
      die.style.borderRadius = '50%'; // d100: círculo
    }

    // Escala compensatória para formas menores visualmente
    if (sc !== 1.0) {
      die.style.transform = 'scale(' + sc + ')';
      die.style.transformOrigin = 'center center';
    }

    // Número
    var num = document.createElement('div');
    num.className = 'mb-die-num';
    num.textContent = value;
    die.appendChild(num);

    // Rótulo tipo dado (d4, d8…)
    var lbl = document.createElement('div');
    lbl.className = 'mb-die-label';
    lbl.textContent = label;
    die.appendChild(lbl);

    return die;
  }

  // Classe CSS do brilho por tipo de dado
  function glowClass(sides) {
    if (sides === 6)   return 'mb-glow-sq';
    if (sides === 4 || sides === 20)  return 'mb-glow-tri';
    if (sides === 8)   return 'mb-glow-dia';
    if (sides === 100) return 'mb-glow-circ';
    return 'mb-glow-pent'; // d10, d12
  }

  // ─────────────────────────────────────────────────────────────
  //  Posições de pouso
  // ─────────────────────────────────────────────────────────────
  function landingPositions(count) {
    var vw  = window.innerWidth;
    var vh  = window.innerHeight;
    var cx  = vw / 2;
    var cy  = vh * 0.56;
    var sp  = Math.min(108, (vw * 0.65) / Math.max(count, 1));
    var pos = [];
    for (var i = 0; i < count; i++) {
      var lx = cx + (i - (count - 1) / 2) * sp - HALF;
      var ly = cy - HALF + r(-16, 16);
      pos.push({ x: lx, y: ly });
    }
    return pos;
  }

  function startPos(i) {
    var vw = window.innerWidth;
    var t  = i % 3;
    if (t === 0) return { x: r(-130, vw * 0.15), y: r(-140, -90) };
    if (t === 1) return { x: r(vw * 0.35, vw * 0.65), y: r(-160, -90) };
    return { x: r(vw * 0.85, vw + 100), y: r(-140, -90) };
  }

  // ─────────────────────────────────────────────────────────────
  //  API pública
  // ─────────────────────────────────────────────────────────────
  var hideTimer       = null;
  var settleTimer     = null;
  var cleanupSubTimer = null;
  var cleanupFns      = [];

  window.DiceAnimator = {

    roll: function (rolls, sides, author, onSettled) {
      if (!rolls || rolls.length === 0) {
        if (onSettled) onSettled();
        return;
      }

      // Apenas d6 tem animação visual — demais dados entregam o resultado direto
      if (sides !== 6) {
        if (onSettled) onSettled();
        return;
      }

      // Cancela animação anterior
      clearTimeout(hideTimer);
      clearTimeout(settleTimer);
      clearTimeout(cleanupSubTimer);
      cleanupFns.forEach(function(fn) { fn(); });
      cleanupFns = [];
      overlay.innerHTML = '';

      var isD6   = true;
      var lands  = landingPositions(rolls.length);
      var movers = [];

      rolls.forEach(function (result, i) {
        var id    = uid();
        var delay = i * 90;
        var s     = startPos(i);
        var land  = lands[i];
        var bH    = r(14, 26);

        // ── Keyframes de movimento (arco + quique) ──
        var mvName = 'mbmv' + id;
        var mx  = (s.x + land.x) / 2;
        var my  = Math.min(s.y, land.y) - r(100, 220);
        var mvKF = '@keyframes ' + mvName + '{' +
          '0%  {transform:translate(' + s.x.toFixed(1) + 'px,' + s.y.toFixed(1) + 'px) scale(.65);}' +
          '30% {transform:translate(' + mx.toFixed(1) + 'px,' + my.toFixed(1) + 'px) scale(1.06);}' +
          '68% {transform:translate(' + land.x.toFixed(1) + 'px,' + (land.y + bH).toFixed(1) + 'px) scale(1);}' +
          '78% {transform:translate(' + land.x.toFixed(1) + 'px,' + (land.y - bH * .55).toFixed(1) + 'px) scale(1.05,.93);}' +
          '86% {transform:translate(' + land.x.toFixed(1) + 'px,' + (land.y + bH * .2).toFixed(1) + 'px) scale(.97,1.05);}' +
          '93% {transform:translate(' + land.x.toFixed(1) + 'px,' + (land.y - bH * .08).toFixed(1) + 'px) scale(1.01,.99);}' +
          '100%{transform:translate(' + land.x.toFixed(1) + 'px,' + land.y.toFixed(1) + 'px) scale(1);}' +
          '}';

        // ── Keyframes de rotação ──
        var spName = 'mbsp' + id;
        var spKF;

        if (isD6) {
          // D6: tumble 3D completo, trava na face correta ao pousar
          var fr = FACE_ROT[result] || [0, 0];
          spKF = '@keyframes ' + spName + '{' +
            '0%  {transform:rotateX(0deg) rotateY(0deg) rotateZ(' + r(-25,25).toFixed(0) + 'deg);}' +
            '25% {transform:rotateX(' + r(-360,-540).toFixed(0) + 'deg) rotateY(' + r(360,540).toFixed(0) + 'deg) rotateZ(' + r(-15,15).toFixed(0) + 'deg);}' +
            '50% {transform:rotateX(' + r(270,450).toFixed(0) + 'deg) rotateY(' + r(-270,-450).toFixed(0) + 'deg) rotateZ(' + r(-6,6).toFixed(0) + 'deg);}' +
            '68% {transform:rotateX(' + fr[0] + 'deg) rotateY(' + fr[1] + 'deg) rotateZ(0deg);}' +
            '100%{transform:rotateX(' + fr[0] + 'deg) rotateY(' + fr[1] + 'deg) rotateZ(0deg);}' +
            '}';
        } else {
          // Não-d6: gira no ar (rotateY = flip de moeda), para horizontal ao pousar
          // Adiciona inclinação extra (rotateZ) durante o voo para mais dinamismo
          var spinY  = r(4, 6) * 360;
          var spinZ1 = r(-180, 180);
          var spinZ2 = r(-90,  90);
          spKF = '@keyframes ' + spName + '{' +
            '0%  {transform:rotateY(0deg)          rotateZ(' + r(-25,25).toFixed(0) + 'deg);}' +
            '25% {transform:rotateY(' + (spinY * 0.3).toFixed(0) + 'deg) rotateZ(' + spinZ1.toFixed(0) + 'deg);}' +
            '50% {transform:rotateY(' + (spinY * 0.6).toFixed(0) + 'deg) rotateZ(' + spinZ2.toFixed(0) + 'deg);}' +
            '68% {transform:rotateY(' + spinY.toFixed(0) + 'deg) rotateZ(0deg);}' +
            '100%{transform:rotateY(' + spinY.toFixed(0) + 'deg) rotateZ(0deg);}' +
            '}';
        }

        // Injeta keyframes
        var kfS = injectKF(mvKF + spKF);
        cleanupFns.push(function() { if (kfS.parentNode) kfS.parentNode.removeChild(kfS); });

        // ── Monta elementos ──
        var mover = document.createElement('div');
        mover.className = 'mb-mv ' + (isD6 ? 'mb-mv--cube' : 'mb-mv--die');
        mover.style.animation = mvName + ' ' + T_FLY + 'ms cubic-bezier(.28,.46,.4,.94) ' + delay + 'ms both';

        var persp = document.createElement('div');
        persp.className = 'mb-persp';

        // Brilho — shape-specific
        var glow = document.createElement('div');
        glow.className = 'mb-glow ' + glowClass(sides);
        persp.appendChild(glow);

        var shadow = document.createElement('div');
        shadow.className = 'mb-shadow';
        persp.appendChild(shadow);

        if (isD6) {
          // Cubo 3D com faces e pontos
          var cube = document.createElement('div');
          cube.className = 'mb-cube';
          cube.style.animation = spName + ' ' + T_FLY + 'ms cubic-bezier(.5,.05,.5,.95) ' + delay + 'ms both';
          for (var f = 1; f <= 6; f++) cube.appendChild(buildFace(f));
          persp.appendChild(cube);
        } else {
          // Dado com forma geométrica característica
          var dieEl = buildDieEl(sides, result);
          dieEl.style.animation = spName + ' ' + T_FLY + 'ms cubic-bezier(.4,0,.2,1) ' + delay + 'ms both';
          persp.appendChild(dieEl);
        }

        mover.appendChild(persp);
        overlay.appendChild(mover);
        movers.push(mover);

        // Sombra aparece ao se aproximar do chão
        var landDelay = delay + T_FLY * 0.65;
        setTimeout(function(m) { m.classList.add('mb-land'); }, landDelay, mover);

        // Brilho ao pousar
        setTimeout(function(m) { m.classList.add('mb-settle'); }, delay + T_FLY, mover);
      });

      // ── Callback: resultado no chat (quando último dado pousa) ──
      var lastDelay = (rolls.length - 1) * 90;
      settleTimer = setTimeout(function () {
        if (onSettled) onSettled();
      }, lastDelay + T_FLY + 80);

      // ── Fade-out dos dados após exibição ──
      hideTimer = setTimeout(function () {
        movers.forEach(function (m) {
          m.style.transition = 'opacity ' + T_FADE + 'ms ease';
          m.style.opacity    = '0';
        });
        cleanupSubTimer = setTimeout(function () {
          overlay.innerHTML = '';
          cleanupFns.forEach(function(fn) { fn(); });
          cleanupFns = [];
        }, T_FADE + 100);
      }, lastDelay + T_FLY + T_SHOW);
    }
  };

  // ═══════════════════════════════════════════════════════════════
  //  Dice Skin System
  // ═══════════════════════════════════════════════════════════════
  var skinLink = null;
  var currentSkin = 'classic';

  DiceAnimator.setSkin = function(skinName) {
    var validSkins = ['classic', 'marble', 'obsidian', 'ruby', 'sapphire', 'emerald', 'gold', 'silver', 'dragon'];
    if (validSkins.indexOf(skinName) === -1) {
      console.warn('DiceAnimator.setSkin: unknown skin "' + skinName + '"');
      return;
    }
    currentSkin = skinName;
    if (!skinLink) {
      skinLink = document.createElement('link');
      skinLink.rel = 'stylesheet';
      skinLink.href = '/core/dice-skins.css';
      document.head.appendChild(skinLink);
    }
    document.documentElement.setAttribute('data-dice-skin', skinName);
    try {
      localStorage.setItem('tvtt-dice-skin', skinName);
    } catch(e) {}
  };

  DiceAnimator.getSkin = function() {
    return currentSkin;
  };

  // Auto-load saved skin (fallback para 'classic' se nenhuma foi salva)
  (function() {
    try {
      var saved = localStorage.getItem('tvtt-dice-skin');
      DiceAnimator.setSkin(saved || 'classic');
    } catch(e) {
      DiceAnimator.setSkin('classic');
    }
  })();

})();
