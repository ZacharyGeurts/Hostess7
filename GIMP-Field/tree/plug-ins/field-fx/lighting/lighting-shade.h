/* AmmoOS Image — field research rewrite (G16 field_opt).
 * RTX-gated paths: see GIMP-Field/data/rtx-gated-content.json
 * OS brand: AmmoOS · product: AmmoOS Image 1.0
 */
#ifndef __LIGHTING_SHADE_H__
#define __LIGHTING_SHADE_H__

typedef void (* get_ray_func) (GimpVector3 *vector,
                               gdouble     *color_sum);

void get_ray_color                 (GimpVector3 *position,
                                    gdouble     *color_sum);
void get_ray_color_no_bilinear     (GimpVector3 *position,
                                    gdouble     *color_sum);
void get_ray_color_ref             (GimpVector3 *position,
                                    gdouble     *color_sum);
void get_ray_color_no_bilinear_ref (GimpVector3 *position,
                                    gdouble     *color_sum);

void    precompute_init               (gint         w,
                                       gint         h);
void    precompute_normals            (gint         x1,
                                       gint         x2,
                                       gint         y);
void    interpol_row                  (gint         x1,
                                       gint         x2,
                                       gint         y);

#endif  /* __LIGHTING_SHADE_H__ */
