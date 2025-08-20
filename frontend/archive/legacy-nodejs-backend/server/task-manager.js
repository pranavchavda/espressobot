import fs from 'fs/promises';
import path from 'path';

export async function saveTaskPlan(filePath, content) {
  try {
    const dir = path.dirname(filePath);
    await fs.mkdir(dir, { recursive: true });
    await fs.writeFile(filePath, content, 'utf-8');
    return true;
  } catch (error) {
    console.error('Error saving task plan:', error);
    return false;
  }
}

export async function loadTaskPlan(filePath) {
  try {
    const content = await fs.readFile(filePath, 'utf-8');
    return content;
  } catch (error) {
    // File doesn't exist or can't be read
    return null;
  }
}