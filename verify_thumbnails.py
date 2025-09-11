#!/usr/bin/env python3
"""
快速验证缩略图尺寸和比例
"""

import os
from PIL import Image

def verify_thumbnails():
    print("🔍 验证9:16缩略图...")
    
    thumbnail_dir = "outputs/images/thumbnails/2025/09"
    
    if not os.path.exists(thumbnail_dir):
        print("❌ 缩略图目录不存在")
        return False
    
    thumbnail_files = [f for f in os.listdir(thumbnail_dir) if f.endswith('.jpg')]
    
    if not thumbnail_files:
        print("❌ 没有找到缩略图文件")
        return False
    
    print(f"📁 找到 {len(thumbnail_files)} 个缩略图文件")
    
    for i, filename in enumerate(thumbnail_files, 1):
        filepath = os.path.join(thumbnail_dir, filename)
        
        try:
            with Image.open(filepath) as img:
                width, height = img.size
                ratio = width / height
                expected_ratio = 9 / 16  # 0.5625
                
                print(f"   {i}. {filename}")
                print(f"      尺寸: {width} x {height}")
                print(f"      比例: {ratio:.4f} (期望: {expected_ratio:.4f})")
                
                # 检查比例是否接近9:16
                if abs(ratio - expected_ratio) < 0.01:
                    print(f"      ✅ 比例正确 (TikTok 9:16)")
                else:
                    print(f"      ❌ 比例错误")
                
                # 检查具体尺寸是否是270x480
                if width == 270 and height == 480:
                    print(f"      ✅ 尺寸完全正确 (270x480)")
                else:
                    print(f"      ⚠️  尺寸与预期不同 (期望: 270x480)")
                
                print()
                
        except Exception as e:
            print(f"   ❌ 无法处理 {filename}: {e}")
    
    return True

def check_file_access():
    print("🔍 检查文件访问...")
    
    # 检查原始文件
    original_dir = "outputs/images/2025/09"
    if os.path.exists(original_dir):
        original_files = [f for f in os.listdir(original_dir) if f.endswith('.png')]
        print(f"📁 原始文件: {len(original_files)} 个")
        
        for filename in original_files:
            filepath = os.path.join(original_dir, filename)
            size = os.path.getsize(filepath)
            print(f"   ✅ {filename} ({size:,} bytes)")
    
    # 检查缩略图文件
    thumbnail_dir = "outputs/images/thumbnails/2025/09"
    if os.path.exists(thumbnail_dir):
        thumbnail_files = [f for f in os.listdir(thumbnail_dir) if f.endswith('.jpg')]
        print(f"📁 缩略图文件: {len(thumbnail_files)} 个")
        
        for filename in thumbnail_files:
            filepath = os.path.join(thumbnail_dir, filename)
            size = os.path.getsize(filepath)
            print(f"   ✅ {filename} ({size:,} bytes)")

if __name__ == "__main__":
    print("🧪 快速缩略图验证")
    print("=" * 50)
    
    check_file_access()
    print()
    verify_thumbnails()
    
    print("✨ 验证完成!")
    print("\n📱 9:16比例说明:")
    print("   - TikTok标准竖屏比例")
    print("   - 270x480像素 = 9:16比例")
    print("   - 适合移动设备竖屏显示")