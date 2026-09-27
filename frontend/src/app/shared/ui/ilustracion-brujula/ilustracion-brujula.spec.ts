import { TestBed } from '@angular/core/testing';

import { IlustracionBrujula } from './ilustracion-brujula';

describe('IlustracionBrujula', () => {
  it('es decorativa y respeta el tamaño', async () => {
    const fixture = TestBed.createComponent(IlustracionBrujula);
    fixture.componentRef.setInput('tamano', 96);
    await fixture.whenStable();
    const svg = (fixture.nativeElement as HTMLElement).querySelector('svg') as SVGElement;
    expect(svg.getAttribute('aria-hidden')).toBe('true');
    expect(svg.getAttribute('width')).toBe('96');
  });
});
