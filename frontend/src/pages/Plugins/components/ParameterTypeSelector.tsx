import React from 'react';
import { FormControl, Select, MenuItem, FormHelperText } from '@mui/material';
import { useTranslation } from 'react-i18next';

interface ParameterTypeSelectorProps {
  value: string | number;
  onChange: (value: string | number) => void;
  error?: boolean;
  helperText?: string;
  useNumericValues?: boolean;
}

const basicTypes = ['string', 'int', 'float', 'boolean', 'object', 'array'] as const;
const arrayElementTypes = ['string', 'int', 'float', 'boolean'] as const;

const numericTypeMap: Record<string, number> = {
  'string': 1,
  'int': 2,
  'float': 3,
  'boolean': 4,
  'object': 5,
  'array_string': 6,
  'array_int': 7,
  'array_float': 8,
  'array_boolean': 9,
};

const stringTypeMap: Record<number, string> = {
  1: 'string',
  2: 'int',
  3: 'float',
  4: 'boolean',
  5: 'object',
  6: 'array_string',
  7: 'array_int',
  8: 'array_float',
  9: 'array_boolean',
};

export const ParameterTypeSelector: React.FC<ParameterTypeSelectorProps> = ({
  value,
  onChange,
  error = false,
  helperText,
  useNumericValues = false,
}) => {
  const { t } = useTranslation();

  const parseType = (typeValue: string | number): { baseType: string; elementType?: string } => {
    let stringValue: string;
    if (useNumericValues) {
      stringValue = stringTypeMap[typeValue as number] || 'string';
    } else {
      stringValue = typeValue as string;
    }

    if (stringValue.startsWith('array_')) {
      return { baseType: 'array', elementType: stringValue.replace('array_', '') };
    }
    return { baseType: stringValue };
  };

  const buildTypeValue = (baseType: string, elementType?: string): string | number => {
    if (baseType === 'array' && elementType) {
      const stringValue = `array_${elementType}`;
      if (useNumericValues) {
        return numericTypeMap[stringValue];
      }
      return stringValue;
    }
    if (useNumericValues) {
      return numericTypeMap[baseType];
    }
    return baseType;
  };

  const currentType = parseType(value);
  const isArrayType = currentType.baseType === 'array';

  const handleBaseTypeChange = (newBaseType: string) => {
    if (newBaseType === 'array') {
      onChange(buildTypeValue('array', 'string'));
    } else {
      onChange(buildTypeValue(newBaseType));
    }
  };

  const handleElementTypeChange = (newElementType: string) => {
    onChange(buildTypeValue('array', newElementType));
  };

  return (
    <div>
      <FormControl fullWidth error={error} sx={{ mb: isArrayType ? 1 : 0 }}>
        <Select
          value={currentType.baseType}
          onChange={(e) => handleBaseTypeChange(e.target.value)}
          displayEmpty
        >
          {basicTypes.map((type) => (
            <MenuItem key={type} value={type}>
              {t(`plugins.toolConfig.parameterTypeOptions.${type}`, getTypeLabel(type))}
            </MenuItem>
          ))}
        </Select>
      </FormControl>

      {isArrayType && (
        <FormControl fullWidth error={error}>
          <Select
            value={currentType.elementType || 'string'}
            onChange={(e) => handleElementTypeChange(e.target.value)}
            displayEmpty
          >
            {arrayElementTypes.map((type) => (
              <MenuItem key={type} value={type}>
                {t(`plugins.toolConfig.parameterTypeOptions.${type}`, getTypeLabel(type))}
              </MenuItem>
            ))}
          </Select>
          <FormHelperText>{t('plugins.toolConfig.arrayElementType', '数组元素类型')}</FormHelperText>
        </FormControl>
      )}

      {helperText && !isArrayType && (
        <FormHelperText error={error}>{helperText}</FormHelperText>
      )}
    </div>
  );
};

function getTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    string: 'String',
    int: 'Int',
    float: 'Float',
    boolean: 'Boolean',
    object: 'Object',
    array: 'Array'
  };
  return labels[type] || type;
}
