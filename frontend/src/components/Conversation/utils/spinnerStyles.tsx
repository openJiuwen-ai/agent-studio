/**
 * iOS风格 Spinner 动画样式组件
 * 用于在多个消息组件中复用
 */
export const IosSpinnerStyles: React.FC = () => (
  <style>{`
    @keyframes ios-spinner {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .ios-spinner {
      position: relative;
      width: 100%;
      height: 100%;
      animation: ios-spinner 1s linear infinite;
    }
    .spinner-dot {
      position: absolute;
      width: 2px;
      height: 5px;
      background-color: rgba(60, 60, 60, 0.9);
      border-radius: 2px;
      left: 50%;
      top: 0;
      transform-origin: 50% 8px;
    }
    .spinner-dot:nth-child(1) { transform: translateX(-50%) rotate(0deg); opacity: 1; }
    .spinner-dot:nth-child(2) { transform: translateX(-50%) rotate(45deg); opacity: 0.85; }
    .spinner-dot:nth-child(3) { transform: translateX(-50%) rotate(90deg); opacity: 0.7; }
    .spinner-dot:nth-child(4) { transform: translateX(-50%) rotate(135deg); opacity: 0.55; }
    .spinner-dot:nth-child(5) { transform: translateX(-50%) rotate(180deg); opacity: 0.4; }
    .spinner-dot:nth-child(6) { transform: translateX(-50%) rotate(225deg); opacity: 0.3; }
    .spinner-dot:nth-child(7) { transform: translateX(-50%) rotate(270deg); opacity: 0.2; }
    .spinner-dot:nth-child(8) { transform: translateX(-50%) rotate(315deg); opacity: 0.15; }
  `}</style>
);

/**
 * 小型 iOS 风格 Spinner 动画样式组件
 * 用于 ReportMessage 等组件
 */
export const IosSpinnerSmallStyles: React.FC = () => (
  <style>{`
    @keyframes ios-spinner-small {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }
    .ios-spinner-small {
      position: relative;
      width: 100%;
      height: 100%;
      animation: ios-spinner-small 1s linear infinite;
    }
    .spinner-dot-small {
      position: absolute;
      width: 1.5px;
      height: 4px;
      background-color: rgba(75, 85, 99, 0.9);
      border-radius: 1.5px;
      left: 50%;
      top: 0;
      transform-origin: 50% 7px;
    }
    .spinner-dot-small:nth-child(1) { transform: translateX(-50%) rotate(0deg); opacity: 1; }
    .spinner-dot-small:nth-child(2) { transform: translateX(-50%) rotate(45deg); opacity: 0.85; }
    .spinner-dot-small:nth-child(3) { transform: translateX(-50%) rotate(90deg); opacity: 0.7; }
    .spinner-dot-small:nth-child(4) { transform: translateX(-50%) rotate(135deg); opacity: 0.55; }
    .spinner-dot-small:nth-child(5) { transform: translateX(-50%) rotate(180deg); opacity: 0.4; }
    .spinner-dot-small:nth-child(6) { transform: translateX(-50%) rotate(225deg); opacity: 0.3; }
    .spinner-dot-small:nth-child(7) { transform: translateX(-50%) rotate(270deg); opacity: 0.2; }
    .spinner-dot-small:nth-child(8) { transform: translateX(-50%) rotate(315deg); opacity: 0.15; }
  `}</style>
);

/**
 * Loading dot 动画样式组件
 * 用于显示加载中的三个点动画
 */
export const LoadingDotStyles: React.FC = () => (
  <style>{`
    @keyframes dot-bounce {
      0%, 80%, 100% { transform: translateY(0); }
      40% { transform: translateY(-4px); }
    }
    .loading-dot {
      animation: dot-bounce 1.4s infinite ease-in-out;
    }
    .loading-dot:nth-child(1) { animation-delay: 0s; }
    .loading-dot:nth-child(2) { animation-delay: 0.2s; }
    .loading-dot:nth-child(3) { animation-delay: 0.4s; }
  `}</style>
);

/**
 * Spinner Dot 组件
 * 用于渲染 iOS 风格的旋转圆点
 */
export const SpinnerDots: React.FC<{ size?: 'normal' | 'small' }> = ({ size = 'normal' }) => {
  const dotCount = 8;
  return (
    <>
      {[...Array(dotCount)].map((_, i) => (
        <div
          key={i}
          className={size === 'normal' ? 'spinner-dot' : 'spinner-dot-small'}
          style={{
            transform: `translateX(-50%) rotate(${i * 45}deg)`
          }}
        />
      ))}
    </>
  );
};
