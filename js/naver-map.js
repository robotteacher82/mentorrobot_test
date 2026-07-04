(function () {
  var CLIENT_ID = 'dw1b0c7ev8';
  var PLACE = {
    name: '멘토로봇코딩교육원',
    address: '대구광역시 달서구 진천로 75-24 3층 (서편)',
    lat: 35.8146314,
    lng: 128.5210393,
    naverUrl: 'https://map.naver.com/p/search/멘토로봇코딩교육원/place/453853050'
  };

  var naverMapInstance = null;
  var loadAttempt = 0;
  var AUTH_PARAMS = ['ncpKeyId', 'ncpClientId'];

  function showMapError(message) {
    var mapEl = document.getElementById('naverMap');
    if (!mapEl) return;
    mapEl.innerHTML = [
      '<div style="display:flex;align-items:center;justify-content:center;height:100%;padding:24px;text-align:center;color:#444;line-height:1.8;font-size:14px;">',
      '<div>', message, '</div>',
      '</div>'
    ].join('');
  }

  function initNaverMap() {
    var mapEl = document.getElementById('naverMap');
    if (!mapEl) return;

    if (typeof naver === 'undefined' || !naver.maps) {
      showMapError(
        '<strong style="color:#c00;">네이버 지도 API 인증 실패</strong><br><br>' +
        '네이버 클라우드 콘솔 → Maps → Application → Web 서비스 URL을<br>' +
        '<code style="background:#eee;padding:2px 6px;">http://localhost</code> 로 등록해 주세요.<br>' +
        '(포트 번호 <code>:8080</code> 은 넣지 않습니다)<br><br>' +
        'API 선택에 <strong>Web Dynamic Map</strong> 이 체크되어 있는지도 확인해 주세요.'
      );
      return;
    }

    mapEl.innerHTML = '';

    var center = new naver.maps.LatLng(PLACE.lat, PLACE.lng);

    naverMapInstance = new naver.maps.Map(mapEl, {
      center: center,
      zoom: 17,
      zoomControl: true,
      zoomControlOptions: { position: naver.maps.Position.TOP_RIGHT },
      mapTypeControl: true,
      scaleControl: true
    });

    var marker = new naver.maps.Marker({
      position: center,
      map: naverMapInstance,
      title: PLACE.name
    });

    var infoWindow = new naver.maps.InfoWindow({
      content: [
        '<div style="padding:10px 12px;min-width:180px;line-height:1.5;">',
        '<strong style="font-size:14px;">', PLACE.name, '</strong><br>',
        '<span style="font-size:12px;color:#555;">', PLACE.address, '</span><br>',
        '<a href="', PLACE.naverUrl, '" target="_blank" rel="noopener" style="font-size:12px;color:#03c75a;font-weight:600;">네이버지도에서 보기</a>',
        '</div>'
      ].join('')
    });

    infoWindow.open(naverMapInstance, marker);

    naver.maps.Event.addListener(marker, 'click', function () {
      if (infoWindow.getMap()) {
        infoWindow.close();
      } else {
        infoWindow.open(naverMapInstance, marker);
      }
    });

    scheduleMapResize();
  }

  function scheduleMapResize() {
    [0, 100, 300, 600].forEach(function (delay) {
      setTimeout(refreshMapSize, delay);
    });
  }

  function refreshMapSize() {
    if (!naverMapInstance) return;
    naver.maps.Event.trigger(naverMapInstance, 'resize');
    naverMapInstance.setCenter(new naver.maps.LatLng(PLACE.lat, PLACE.lng));
  }

  function waitForNaver(callback, timeoutMs) {
    var elapsed = 0;
    var timer = setInterval(function () {
      if (window.naver && naver.maps) {
        clearInterval(timer);
        callback();
      } else if ((elapsed += 100) >= timeoutMs) {
        clearInterval(timer);
        callback();
      }
    }, 100);
  }

  function loadMapScript() {
    if (window.location.protocol === 'file:') {
      showMapError(
        '<strong style="color:#c00;">file:// 로는 지도가 표시되지 않습니다.</strong><br><br>' +
        '터미널에서 <code style="background:#eee;padding:2px 6px;">python -m http.server 8080</code> 실행 후<br>' +
        '<a href="http://localhost:8080" style="color:#03c75a;font-weight:600;">http://localhost:8080</a> 으로 접속해 주세요.'
      );
      return;
    }

    if (loadAttempt >= AUTH_PARAMS.length) {
      showMapError(
        '<strong style="color:#c00;">지도 API를 불러오지 못했습니다.</strong><br><br>' +
        'Client ID와 Web 서비스 URL 설정을 확인해 주세요.'
      );
      return;
    }

    var param = AUTH_PARAMS[loadAttempt];
    loadAttempt += 1;

    var script = document.createElement('script');
    script.src = 'https://oapi.map.naver.com/openapi/v3/maps.js?' + param + '=' + CLIENT_ID;
    script.async = true;

    script.onload = function () {
      waitForNaver(initNaverMap, 3000);
    };

    script.onerror = function () {
      loadMapScript();
    };

    document.head.appendChild(script);
  }

  window.initNaverMap = initNaverMap;
  window.addEventListener('resize', refreshMapSize);
  window.addEventListener('load', scheduleMapResize);

  var locationSection = document.getElementById('location');
  if (locationSection && 'IntersectionObserver' in window) {
    var mapObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          scheduleMapResize();
          mapObserver.disconnect();
        }
      });
    }, { threshold: 0.1 });
    mapObserver.observe(locationSection);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', loadMapScript);
  } else {
    loadMapScript();
  }
})();
