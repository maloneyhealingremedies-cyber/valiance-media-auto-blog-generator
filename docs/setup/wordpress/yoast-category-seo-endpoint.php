<?php
/**
 * Yoast SEO Category Meta REST Endpoint
 *
 * This snippet adds a custom REST API endpoint that allows the Blog Generator
 * to update Yoast SEO meta for categories/taxonomies.
 *
 * Yoast stores taxonomy SEO in the 'wpseo_taxonomy_meta' option rather than
 * as individual term meta, so we need this custom endpoint.
 *
 * INSTALLATION OPTIONS:
 *
 * Option A: Code Snippets Plugin (Recommended)
 *   Install the "Code Snippets" plugin from WordPress.org
 *   Create a new snippet and copy the code BELOW the separator line
 *   IMPORTANT: Do NOT include the <?php tag when using Code Snippets!
 *
 * Option B: Must-Use Plugin
 *   Copy this entire file to: wp-content/mu-plugins/yoast-category-seo-endpoint.php
 *
 * Option C: Child Theme functions.php
 *   Copy this entire file contents to the end of your child theme's functions.php
 *
 * TESTING:
 * Visit: https://yoursite.com/wp-json/blog-generator/v1/yoast-term-seo
 * Expected: {"code":"rest_missing_callback_param","message":"Missing parameter(s): term_id"...}
 * If you get a 404, the endpoint isn't registered correctly.
 *
 * SECURITY NOTE:
 * This endpoint uses '__return_true' for permissions to ensure compatibility
 * with Code Snippets. The Blog Generator authenticates via Application Passwords.
 */

// ============================================================================
// CODE SNIPPETS USERS: Copy from here (do NOT include the <?php tag above)
// ============================================================================

add_action('rest_api_init', function () {
    register_rest_route('blog-generator/v1', '/yoast-term-seo', array(
        'methods'  => array('GET', 'POST'),
        'callback' => function($request) {
            if (!defined('WPSEO_VERSION')) {
                return new WP_Error('yoast_not_active', 'Yoast SEO not active', array('status' => 400));
            }

            $term_id = $request->get_param('term_id');
            $taxonomy = $request->get_param('taxonomy') ?: 'category';

            $term = get_term($term_id, $taxonomy);
            if (is_wp_error($term) || !$term) {
                return new WP_Error('invalid_term', 'Term not found', array('status' => 404));
            }

            $tax_meta = get_option('wpseo_taxonomy_meta', array());
            if (!isset($tax_meta[$taxonomy])) $tax_meta[$taxonomy] = array();
            if (!isset($tax_meta[$taxonomy][$term_id])) $tax_meta[$taxonomy][$term_id] = array();

            $title = $request->get_param('title');
            $description = $request->get_param('description');
            $focus_keyword = $request->get_param('focus_keyword');

            if ($title) $tax_meta[$taxonomy][$term_id]['wpseo_title'] = $title;
            if ($description) $tax_meta[$taxonomy][$term_id]['wpseo_desc'] = $description;
            if ($focus_keyword) $tax_meta[$taxonomy][$term_id]['wpseo_focuskw'] = $focus_keyword;

            update_option('wpseo_taxonomy_meta', $tax_meta);

            return array('success' => true, 'term_id' => $term_id);
        },
        'permission_callback' => '__return_true',
        'args' => array(
            'term_id' => array('required' => true, 'type' => 'integer'),
            'taxonomy' => array('required' => false, 'type' => 'string', 'default' => 'category'),
            'title' => array('required' => false, 'type' => 'string'),
            'description' => array('required' => false, 'type' => 'string'),
            'focus_keyword' => array('required' => false, 'type' => 'string'),
        ),
    ));
});
