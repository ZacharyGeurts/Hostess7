/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
#ifndef __LIGHTING_APPLY_H__
#define __LIGHTING_APPLY_H__

void init_compute     (void);
void compute_image    (void);
void copy_from_config (GimpProcedureConfig *config);

#endif  /* __LIGHTING_APPLY_H__ */
