import * as React from "react";

interface AiLoaderProps {
  size?: number;
  text?: string;
}

export const AiLoader: React.FC<AiLoaderProps> = ({
  size = 180,
  text = "Generating",
}) => {
  const letters = text.split("");

  return (
    <div className="flex flex-col items-center justify-center gap-6">
      <div
        className="relative flex items-center justify-center select-none flex-wrap gap-0.5"
        style={{ width: size, height: size }}
      >
        {/* Animated circle ring */}
        <div
          className="absolute inset-0 rounded-full animate-[loaderCircle_5s_linear_infinite]"
        />

        {/* Animated letters */}
        <div className="relative flex flex-wrap justify-center items-center gap-px px-4">
          {letters.map((letter, index) => (
            <span
              key={index}
              className="inline-block text-blue-600 font-medium text-sm opacity-40 animate-[loaderLetter_3s_infinite]"
              style={{ animationDelay: `${index * 0.1}s` }}
            >
              {letter === " " ? "\u00A0" : letter}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
};
