import {defineConfig} from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins:[react()],
  build:{target:'es2022',sourcemap:false,manifest:true},
  test:{include:['src/**/*.test.ts'],environment:'node',maxWorkers:1},
});
