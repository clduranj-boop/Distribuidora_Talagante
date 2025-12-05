import { initPasswordValidation } from './password.js';
import { initRutValidation } from './rut.js';

export function initRegisterValidation() {
    initPasswordValidation();
    initRutValidation();
    console.log('Validaciones de registro cargadas');
}