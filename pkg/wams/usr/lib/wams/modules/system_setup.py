"""
Sistema de detección y configuración automática de entorno
Compatible con cualquier hardware en distribuciones Arch-based con Plasma 6
"""

import os
import subprocess
from typing import Dict, Optional

class SystemConfig:
    """Maneja la detección de hardware y configuración del entorno"""
    
    def __init__(self):
        self.gpu_vendor: str = 'unknown'
        self.session_type: str = 'unknown'
        self.gpu_info: Dict[str, str] = {}
        self.strategy_used: str = 'unknown'
        
    def detect_gpu(self) -> str:
        """
        Detecta el fabricante de la GPU principal
        Returns: 'nvidia', 'amd', 'intel' o 'unknown'
        """
        # Método 1: lspci (más confiable y rápido)
        try:
            result = subprocess.run(
                ['lspci', '-nn'], 
                capture_output=True, 
                text=True, 
                timeout=2
            )
            output = result.stdout.lower()
            
            # Buscar líneas VGA/3D
            for line in output.split('\n'):
                if 'vga' in line or '3d' in line or 'display' in line:
                    if 'nvidia' in line:
                        self.gpu_info['model'] = line
                        return 'nvidia'
                    elif 'amd' in line or 'radeon' in line or 'advanced micro devices' in line:
                        self.gpu_info['model'] = line
                        return 'amd'
                    elif 'intel' in line:
                        self.gpu_info['model'] = line
                        return 'intel'
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            print(f"Warning: lspci detection failed: {e}")
        
        # Método 2: glxinfo (fallback)
        try:
            result = subprocess.run(
                ['glxinfo'], 
                capture_output=True, 
                text=True, 
                timeout=2
            )
            output = result.stdout.lower()
            
            if 'nvidia' in output:
                return 'nvidia'
            elif 'amd' in output or 'radeon' in output:
                return 'amd'
            elif 'intel' in output:
                return 'intel'
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
            pass
        
        # Método 3: Leer directamente desde /sys
        try:
            card_path = '/sys/class/drm/card0/device/vendor'
            if os.path.exists(card_path):
                with open(card_path, 'r') as f:
                    vendor_id = f.read().strip()
                
                # IDs PCI de fabricantes
                vendor_map = {
                    '0x10de': 'nvidia',
                    '0x1002': 'amd',
                    '0x1022': 'amd',
                    '0x8086': 'intel'
                }
                
                return vendor_map.get(vendor_id, 'unknown')
        except (IOError, OSError):
            pass
        
        return 'unknown'
    
    def detect_session_type(self) -> str:
        """
        Detecta el tipo de sesión gráfica
        Returns: 'wayland', 'x11' o 'unknown'
        """
        session = os.environ.get('XDG_SESSION_TYPE', '').lower()
        
        if session in ['wayland', 'x11']:
            return session
        
        # Fallback: verificar WAYLAND_DISPLAY
        if os.environ.get('WAYLAND_DISPLAY'):
            return 'wayland'
        
        # Fallback: verificar DISPLAY (X11)
        if os.environ.get('DISPLAY'):
            return 'x11'
        
        return 'unknown'
    
    def get_nvidia_driver_version(self) -> Optional[str]:
        """Obtiene la versión del driver NVIDIA si está instalado"""
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None
    
    def check_qt_wayland_available(self) -> bool:
        """Verifica si Qt tiene soporte Wayland compilado"""
        try:
            result = subprocess.run(
                ['pkg-config', '--exists', 'Qt6WaylandClient'],
                capture_output=True,
                timeout=1
            )
            return result.returncode == 0
        except:
            return False
    
    def apply_nvidia_config(self, chromium_flags: list) -> None:
        """
        Aplica configuración específica para GPUs NVIDIA
        Estrategia: Probar múltiples configuraciones en orden de preferencia
        """
        print("🟢 NVIDIA GPU detected - Applying optimizations")
        
        # Verificar driver
        driver_version = self.get_nvidia_driver_version()
        if driver_version:
            print(f"   NVIDIA Driver version: {driver_version}")
        
        # Determinar estrategia basada en safe_mode
        safe_mode = os.environ.get('WAMS_SAFE_MODE', '0') == '1'
        
        if safe_mode:
            self._apply_nvidia_software_rendering(chromium_flags)
            return
        
        # ESTRATEGIA PRINCIPAL: Forzar XCB con renderizado software
        # Esta es la más estable para NVIDIA + Wayland + Qt6 WebEngine
        if self.session_type == 'wayland':
            print("   ⚙️  Strategy: XCB + Software Rendering (most stable)")
            self.strategy_used = 'xcb_software'
            
            # Forzar XCB (X11 compatibility layer en Wayland)
            os.environ['QT_QPA_PLATFORM'] = 'xcb'
            
            # Deshabilitar aceleración GPU para Qt WebEngine
            # (NVIDIA + Wayland + EGL es problemático)
            chromium_flags.extend([
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-dev-shm-usage',
                '--renderer-process-limit=4',
                '--process-per-site',
                '--js-flags="--max-old-space-size=512"',
                '--disable-extensions',
            ])
            
            print("   ℹ️  GPU acceleration disabled for stability")
            print("   ℹ️  Performance may be reduced but stability is guaranteed")
            
        else:
            # X11 nativo - podemos intentar aceleración
            print("   ✅ Strategy: X11 + Hardware Acceleration")
            self.strategy_used = 'x11_hardware'
            
            chromium_flags.extend([
                '--use-gl=desktop',
                '--ignore-gpu-blocklist',
                '--enable-gpu-rasterization',
                '--disable-gpu-driver-bug-workarounds',
            ])
        
        # Optimizaciones comunes NVIDIA
        os.environ['__GL_THREADED_OPTIMIZATIONS'] = '1'
        os.environ['__GL_SYNC_TO_VBLANK'] = '0'
    
    def _apply_nvidia_software_rendering(self, chromium_flags: list) -> None:
        """Modo software rendering puro - máxima compatibilidad"""
        print("   🔧 Using SOFTWARE RENDERING mode (safe fallback)")
        self.strategy_used = 'software'
        
        if self.session_type == 'wayland':
            os.environ['QT_QPA_PLATFORM'] = 'xcb'
        
        chromium_flags.extend([
            '--disable-gpu',
            '--disable-gpu-compositing',
            '--disable-software-rasterizer',
            '--renderer-process-limit=4',
            '--process-per-site',
            '--js-flags="--max-old-space-size=512"',
            '--disable-extensions',
        ])
        
        os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
    
    def apply_amd_config(self, chromium_flags: list) -> None:
        """Aplica configuración específica para GPUs AMD"""
        print("🔴 AMD GPU detected - Applying optimizations")
        self.strategy_used = 'amd_default'
        
        # AMD funciona mejor con EGL en ambos X11 y Wayland
        chromium_flags.extend([
            '--enable-gpu-rasterization',
            '--enable-features=VaapiVideoDecoder',
            '--use-gl=egl',
        ])
        
        # Optimizaciones Mesa
        os.environ.setdefault('mesa_glthread', 'true')
    
    def apply_intel_config(self, chromium_flags: list) -> None:
        """Aplica configuración específica para GPUs Intel"""
        print("🔵 Intel GPU detected - Applying optimizations")
        self.strategy_used = 'intel_default'
        
        chromium_flags.extend([
            '--enable-gpu-rasterization',
            '--enable-features=VaapiVideoDecoder',
            '--use-gl=egl',
        ])
    
    def apply_generic_config(self, chromium_flags: list) -> None:
        """Configuración conservadora para hardware desconocido"""
        print("⚪ Unknown GPU - Applying generic configuration")
        self.strategy_used = 'generic'
        
        chromium_flags.extend([
            '--disable-gpu-sandbox',
            '--disable-software-rasterizer',
        ])
    
    def setup(self) -> None:
        """Configura el entorno completo según el hardware detectado"""
        print("\n" + "="*60)
        print("🚀 WAms - System Configuration")
        print("="*60)
        
        # Detectar sistema
        self.gpu_vendor = self.detect_gpu()
        self.session_type = self.detect_session_type()
        
        print(f"📊 Session type: {self.session_type.upper()}")
        print(f"🎮 GPU vendor: {self.gpu_vendor.upper()}")
        
        if self.gpu_info.get('model'):
            print(f"   Model: {self.gpu_info['model'][:80]}")
        
        # Flags base de Chromium (seguros para todos)
        chromium_flags = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-seccomp-filter-sandbox',
            '--disable-dev-shm-usage',
            '--autoplay-policy=no-user-gesture-required',
            '--enable-features=WebRTCPipeWireCapturer',
            '--use-fake-ui-for-media-stream',
            '--enable-webrtc-hw-encoding',
            '--enable-webrtc-hw-decoding',
            '--enable-low-end-device-mode',
            '--disable-background-networking',
            '--disable-component-update',
            '--disable-features=Translate,OptimizationHints,MediaRouter,DialMediaRouteProvider,DesktopPWAsWithoutWebAppELMetadata',
        ]
        
        # Aplicar configuración según GPU
        config_methods = {
            'nvidia': self.apply_nvidia_config,
            'amd': self.apply_amd_config,
            'intel': self.apply_intel_config,
            'unknown': self.apply_generic_config,
        }
        
        config_methods[self.gpu_vendor](chromium_flags)
        
        # Configurar flags de Chromium
        os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = ' '.join(chromium_flags)
        
        # Prevenir warning de decoraciones en Wayland
        if self.session_type == 'wayland':
            os.environ.setdefault('QT_WAYLAND_DISABLE_WINDOWDECORATION', '1')
        
        # Configuración Qt adicional
        os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')
        
        print(f"\n✅ Environment configured successfully")
        print(f"   Strategy: {self.strategy_used}")
        print(f"   Platform: {os.environ.get('QT_QPA_PLATFORM', 'default')}")
        print("="*60 + "\n")


def initialize_environment():
    """
    Función principal para inicializar el entorno.
    Debe ser llamada ANTES de importar cualquier módulo de Qt.
    """
    config = SystemConfig()
    config.setup()
    return config