import '@testing-library/jest-dom';
import { server } from './mocks/server';

// MSW server setup
beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
