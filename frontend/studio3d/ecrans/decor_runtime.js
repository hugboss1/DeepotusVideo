/* deepotus-decor-vent.js — runtime de vent pour la végétation exportée par le Décor du 3D Studio (DeepotusVideo).
   À copier dans votre projet three.js, à côté du GLB et de la recette `.decor.json`.

   Usage :
     import { ajouterVent } from "./deepotus-decor-vent.js";
     const gltf = await new GLTFLoader().loadAsync("chene.glb");
     scene.add(gltf.scene);
     const recette = await (await fetch("chene.decor.json")).json();
     const vent = ajouterVent(gltf.scene, recette);        // recette facultative : réglages par défaut sinon
     renderer.setAnimationLoop((t) => { vent.maj(t / 1000); renderer.render(scene, camera); });
     vent.regler({ reglages: { ventForce: 0.3 } });         // changer le vent en cours de route

   Deux cas :
   - un maillage nommé « dz_feuilles » (arbre du Décor) ondule feuille par feuille : le décalage croît avec la
     coordonnée de texture v (le bout de la feuille bouge, sa base reste attachée), trois sinusoïdes de fréquences
     1, 2 et 5, déphasées par la position. C'est le principe du shader d'ez-tree (MIT), sans son bruit simplex ;
   - un maillage qui porte l'attribut `_WIND` (masque de vent écrit par Décor › Accessoire : 0 au pied, 1 au sommet ;
     GLTFLoader le livre sous le nom `_wind`) plie d'un bloc : le décalage vaut masque × force, la phase est celle de
     l'objet entier (pas de déchirure entre sommets voisins). `ventForce` = le déplacement du sommet, en mètres. */

export function parametres(recette) {
  const r = (recette && recette.reglages) || {};
  if (r.vent === false) return { force: [0, 0, 0], frequence: 0, echelle: 70 };
  const a = ((r.ventDirection ?? 42) * Math.PI) / 180, f = r.ventForce ?? 0.7;
  return { force: [Math.cos(a) * f, 0, Math.sin(a) * f], frequence: 0.5 * (r.ventVitesse ?? 1.1),
    echelle: 70 / Math.max(0.2, (r.frisson ?? 5) / 5) };
}

const PHASE_FEUILLE = "float phase = 6.2832 * fract(dot(mvPosition.xyz, vec3(0.13, 0.07, 0.11)) * 70.0 / uEchelle);";
const PHASE_OBJET = "float phase = 6.2832 * fract(dot(modelMatrix[3].xyz, vec3(0.13, 0.07, 0.11)));";

export function ajouterVent(racine, recette) {
  let p = parametres(recette);
  const shaders = [];
  racine.traverse((o) => {
    if (!o.isMesh) return;
    const masque = o.geometry && o.geometry.getAttribute && o.geometry.getAttribute("_wind");
    if (!masque && o.name !== "dz_feuilles") return;
    if (masque) {
      o.geometry.setAttribute("dzVent", masque);        // un nom de GLSL sûr (pas de « _ » en tête)
      o.material = o.material.clone();                   // ce programme-ci attend l'attribut : matériau à lui
      o.material.customProgramCacheKey = () => "dz-vent-masque";
    }
    const facteur = masque ? "dzVent" : "uv.y";
    o.material.onBeforeCompile = (shader) => {
      shader.uniforms.uTemps = { value: 0 };
      shader.uniforms.uForce = { value: p.force };
      shader.uniforms.uFrequence = { value: p.frequence };
      shader.uniforms.uEchelle = { value: p.echelle };
      shader.vertexShader = "uniform float uTemps; uniform vec3 uForce; uniform float uFrequence; uniform float uEchelle;\n"
        + (masque ? "attribute float dzVent;\n" : "")
        + shader.vertexShader.replace("#include <project_vertex>", `
          vec4 mvPosition = vec4(transformed, 1.0);
          #ifdef USE_INSTANCING
            mvPosition = instanceMatrix * mvPosition;
          #endif
          mvPosition = modelViewMatrix * mvPosition;
          ${masque ? PHASE_OBJET : PHASE_FEUILLE}
          vec3 balancement = ${facteur} * uForce * (0.5 * sin(uTemps * uFrequence + phase)
            + 0.3 * sin(2.0 * uTemps * uFrequence + 1.3 * phase) + 0.2 * sin(5.0 * uTemps * uFrequence + 1.5 * phase));
          mvPosition.xyz += (viewMatrix * vec4(balancement, 0.0)).xyz;
          gl_Position = projectionMatrix * mvPosition;`);
      shaders.push(shader);
    };
    o.material.needsUpdate = true;
  });
  return {
    maj(t) { for (const s of shaders) s.uniforms.uTemps.value = t; },
    regler(r) {
      p = parametres(r);
      for (const s of shaders) {
        s.uniforms.uForce.value = p.force;
        s.uniforms.uFrequence.value = p.frequence;
        s.uniforms.uEchelle.value = p.echelle;
      }
    },
  };
}
